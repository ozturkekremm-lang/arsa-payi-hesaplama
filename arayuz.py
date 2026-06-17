import streamlit as st
import pandas as pd
import math
from functools import reduce


def ekok_bul(sayilar):
    sayilar = [s for s in sayilar if s and s > 0]
    if not sayilar: return 1

    def lcm(a, b):
        return abs(a * b) // math.gcd(a, b)

    return reduce(lcm, sayilar)


st.set_page_config(page_title="Hata Denetimli Arsa Payı", layout="wide")
st.title("🛡️ Hukuki Denetim ve Otomatik Hak Sağlaması")

# 1. TAPU KAYITLARI
st.sidebar.header("1. Arsa Payı Hakları")
h_input = pd.DataFrame([
    {"Hissedar": "Ahmet Bey", "Pay": 1, "Payda": 4},
    {"Hissedar": "Mehmet Bey", "Pay": 3, "Payda": 4}
])
edited_h = st.sidebar.data_editor(h_input, num_rows="dynamic")

# 2. DAİRELER
st.header("2. Bağımsız Bölümler ve Tahsisler")
d_input = pd.DataFrame([
    {"Daire No": "1", "Brüt m2": 100.0, "Sahibi": "Ahmet Bey", "Tahsis Oranı": 1.0},
    {"Daire No": "2", "Brüt m2": 400.0, "Sahibi": "", "Tahsis Oranı": 0.0}
])
edited_d = st.data_editor(d_input, num_rows="dynamic")

if st.button("HAKLARI DENETLE VE HESAPLA"):
    h_df = edited_h.dropna(subset=["Hissedar", "Pay", "Payda"])
    d_df = edited_d.dropna(subset=["Daire No", "Brüt m2"])

    # 1. HUKUKİ DENETİM: PAYLAR TOPLAMI 1 Mİ?
    toplam_pay_orani = sum(h_df["Pay"] / h_df["Payda"])
    if not math.isclose(toplam_pay_orani, 1.0, rel_tol=1e-9):
        st.error(f"❌ HUKUKİ HATA: Tapu payları toplamı 1 etmiyor! (Toplam: {toplam_pay_orani})")
    else:
        # HESAPLAMA ÖN HAZIRLIĞI
        toplam_m2 = d_df.drop_duplicates(subset=["Daire No"])["Brüt m2"].sum()
        ekok_p = ekok_bul(h_df["Payda"].astype(int).tolist())
        nihai_payda = int(ekok_p * toplam_m2 * 100)

        # Hissedarların Mutlak Arsa Payı Hakları (Tam Sayı)
        h_haklar_orijinal = {str(h["Hissedar"]).strip(): int((h["Pay"] / h["Payda"]) * nihai_payda) for _, h in
                             h_df.iterrows()}
        h_haklar_calisma = h_haklar_orijinal.copy()

        daire_paylari = {}
        daire_ozellikleri = {}
        tahsis_hatasi = False
        hata_mesajlari = []

        # 2. ADIM: TAHSİS DENETİMİ VE DAĞITIM
        for _, d in d_df.iterrows():
            d_no = str(d["Daire No"])
            d_m2 = d["Brüt m2"]
            daire_ozellikleri[d_no] = d_m2
            if d_no not in daire_paylari: daire_paylari[d_no] = {}

            sahibi = str(d["Sahibi"]).strip() if pd.notna(d["Sahibi"]) and str(d["Sahibi"]).strip() != "" else None
            oran = float(d["Tahsis Oranı"]) if pd.notna(d["Tahsis Oranı"]) else 0.0

            if sahibi and oran > 0:
                if sahibi not in h_haklar_calisma:
                    tahsis_hatasi = True
                    hata_mesajlari.append(f"⚠️ {d_no} nolu dairede yazılı '{sahibi}' hissedar listesinde yok!")
                    continue

                d_toplam_pay = int((d_m2 / toplam_m2) * nihai_payda)
                verilecek_pay = int(d_toplam_pay * oran)

                # KRİTİK KONTROL: Kişinin hakkından fazla tahsis yapılıyor mu?
                if verilecek_pay > h_haklar_calisma[sahibi] + 5:  # 5 birim tolerans (yuvarlama için)
                    tahsis_hatasi = True
                    hata_mesajlari.append(
                        f"❌ HAK İHLALİ: {sahibi} adlı kişiye {d_no} nolu dairede hakkından fazla tahsis yapıldı!")
                else:
                    daire_paylari[d_no][sahibi] = daire_paylari[d_no].get(sahibi, 0) + verilecek_pay
                    h_haklar_calisma[sahibi] -= verilecek_pay

        if tahsis_hatasi:
            for msg in hata_mesajlari:
                st.error(msg)
            st.warning("Lütfen tahsis oranlarını veya hissedar haklarını düzeltin.")
        else:
            # 3. ADIM: KALAN BOŞLUKLARI DAĞIT (BAKİYE USULÜ)
            for d_no, d_m2 in daire_ozellikleri.items():
                d_toplam_pay = int((d_m2 / toplam_m2) * nihai_payda)
                mevcut_pay = sum(daire_paylari[d_no].values())
                bos_pay = d_toplam_pay - mevcut_pay

                if bos_pay > 0:
                    for isim, kalan in h_haklar_calisma.items():
                        if kalan > 0:
                            eklenen = min(kalan, bos_pay)
                            daire_paylari[d_no][isim] = daire_paylari[d_no].get(isim, 0) + eklenen
                            h_haklar_calisma[isim] -= eklenen
                            bos_pay -= eklenen
                        if bos_pay <= 0: break

            # 4. ADIM: NİHAİ CETVEL OLUŞTURMA
            final_list = []
            for d_no, m2 in daire_ozellikleri.items():
                d_pay_toplam = int((m2 / toplam_m2) * nihai_payda)
                malikler = {k: v for k, v in daire_paylari[d_no].items() if v > 0}
                first_row = True
                for malik, pay in malikler.items():
                    final_list.append({
                        "B.B. No": d_no if first_row else "",
                        "B.B. m2": m2 if first_row else "",
                        "B.B. Toplam Pay": f"{d_pay_toplam} / {nihai_payda}" if first_row else "",
                        "Malik": malik,
                        "Daire İçi Hisse": f"{pay} / {d_pay_toplam}"
                    })
                    first_row = False

            st.subheader("📋 Resmi Arsa Payı Cetveli")
            st.table(pd.DataFrame(final_list))

            # SON DOĞRULAMA (Eksik hak kaldı mı?)
            for isim, bakiye in h_haklar_calisma.items():
                if bakiye > 10:  # Yuvarlama payı
                    st.error(f"❌ DAĞITIM EKSİK: {isim} adlı hissedarın hala {bakiye} birim alacağı var!")

            st.success("✅ Dağıtım ve hak sağlaması başarıyla tamamlandı. Tüm paylar hukuki sınırlara uygun.")