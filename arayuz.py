import streamlit as st
import pandas as pd
from functools import reduce
import math
from decimal import Decimal, getcontext

# İçsel hesaplama hassasiyetini yüksek tutuyoruz
getcontext().prec = 28


def ekok_bul(sayilar):
    sayilar = [int(s) for s in sayilar if s and s > 0]
    if not sayilar: return 1

    def lcm(a, b):
        return abs(a * b) // math.gcd(a, b)

    return reduce(lcm, sayilar)


def ondalik_basamak_sayisi(val):
    """Bir Decimal sayının virgülden sonraki anlamlı basamak sayısını bulur."""
    s = str(val.normalize())
    if '.' in s:
        return len(s.split('.')[1])
    return 0


st.set_page_config(page_title="Arsa Payı Hesaplama", layout="wide")
st.title("🛡️ Dinamik Ölçeklemeli ve Hassas Arsa Payı Hesaplaması")

# 1. TAPU KAYITLARI
st.sidebar.header("1. Tapu Hisseleri")
h_input = pd.DataFrame([
    {"Hissedar": "Ahmet Bey", "Pay": 1, "Payda": 4},
    {"Hissedar": "Mehmet Bey", "Pay": 2, "Payda": 4},
    {"Hissedar": "Ali Bey", "Pay": 1, "Payda": 4}
])
edited_h = st.sidebar.data_editor(h_input, num_rows="dynamic")

# 2. BAĞIMSIZ BÖLÜM GİRİŞLERİ
st.caption(
    "ℹ *Aynı daireye birden fazla kişi atamak için aynı Daire No ile yeni satır ekleyebilirsiniz. 'Sahibi' ve 'Hissesi' boş bırakılabilir.*")

d_input = pd.DataFrame([
    {"Blok Adı": "A Blok", "Bulunduğu Kat": "1. Kat", "Daire No": "1", "Niteliği": "Mesken", "Brüt m2": 100.0,
     "Sahibi": "Ahmet Bey", "Hissesi": 0.60},
    {"Blok Adı": "A Blok", "Bulunduğu Kat": "1. Kat", "Daire No": "1", "Niteliği": "Mesken", "Brüt m2": 100.0,
     "Sahibi": "Mehmet Bey", "Hissesi": 0.20},
    {"Blok Adı": "A Blok", "Bulunduğu Kat": "Zemin", "Daire No": "2", "Niteliği": "Dükkan", "Brüt m2": 400.0,
     "Sahibi": "", "Hissesi": 0.0}
])
edited_d = st.data_editor(d_input, num_rows="dynamic")

if st.button("HAKLARI DENETLE VE HESAPLA"):
    h_df = edited_h.dropna(subset=["Hissedar", "Pay", "Payda"])
    d_df = edited_d.dropna(subset=["Daire No", "Brüt m2"])

    # 1. HUKUKİ DENETİM
    toplam_pay_orani = sum(Decimal(str(h["Pay"])) / Decimal(str(h["Payda"])) for _, h in h_df.iterrows())

    if toplam_pay_orani != Decimal('1.0'):
        st.error(f"❌ HUKUKİ HATA: Tapu payları toplamı tam olarak 1 etmiyor! (Mevcut Toplam: {toplam_pay_orani})")
    else:
        # 2. ÖN HESAPLAMA (Saf taban)
        toplam_m2 = Decimal(str(d_df.drop_duplicates(subset=["Daire No"])["Brüt m2"].sum()))
        ekok_p = ekok_bul(h_df["Payda"].astype(int).tolist())
        saf_payda = Decimal(str(ekok_p)) * toplam_m2

        # Geçici Haklar ve Dağıtım Hafızası (Ondalık Değerlerle Tutuluyor)
        h_haklar_calisma = {str(h["Hissedar"]).strip(): (Decimal(str(h["Pay"])) / Decimal(str(h["Payda"]))) * saf_payda
                            for _, h in h_df.iterrows()}

        daire_paylari_dec = {}
        daire_ozellikleri = {}
        daire_ilk_sahipleri = {}
        tahsis_hatasi = False
        hata_mesajlari = []

        # Elle Atanan Öncelikli Hisseler
        for _, d in d_df.iterrows():
            d_no = str(d["Daire No"])
            d_m2 = Decimal(str(d["Brüt m2"]))

            if d_no not in daire_ozellikleri:
                daire_ozellikleri[d_no] = {
                    "m2": d_m2,
                    "blok": str(d["Blok Adı"]) if pd.notna(d["Blok Adı"]) else "",
                    "kat": str(d["Bulunduğu Kat"]) if pd.notna(d["Bulunduğu Kat"]) else "",
                    "nitelik": str(d["Niteliği"]) if pd.notna(d["Niteliği"]) else ""
                }

            if d_no not in daire_paylari_dec: daire_paylari_dec[d_no] = {}
            if d_no not in daire_ilk_sahipleri: daire_ilk_sahipleri[d_no] = set()

            sahibi = str(d["Sahibi"]).strip() if pd.notna(d["Sahibi"]) and str(d["Sahibi"]).strip() != "" else None
            oran = Decimal(str(d["Hissesi"])) if pd.notna(d["Hissesi"]) and float(d["Hissesi"]) > 0 else Decimal('0.0')

            if sahibi and oran > 0:
                if sahibi not in h_haklar_calisma:
                    tahsis_hatasi = True
                    hata_mesajlari.append(f"⚠️ {d_no} nolu dairede yazılı '{sahibi}' hissedar listesinde yok!")
                    continue

                d_toplam_pay = (d_m2 / toplam_m2) * saf_payda
                verilecek_pay = d_toplam_pay * oran

                if verilecek_pay > h_haklar_calisma[sahibi]:
                    tahsis_hatasi = True
                    hata_mesajlari.append(
                        f"❌ HAK İHLALİ: {sahibi} adlı kişiye {d_no} nolu dairede hakkından fazla tahsis yapıldı!")
                else:
                    daire_paylari_dec[d_no][sahibi] = daire_paylari_dec[d_no].get(sahibi, Decimal('0')) + verilecek_pay
                    h_haklar_calisma[sahibi] -= verilecek_pay
                    daire_ilk_sahipleri[d_no].add(sahibi)

        if tahsis_hatasi:
            for msg in hata_mesajlari: st.error(msg)
            st.warning("Lütfen tahsis oranlarını veya hissedar haklarını düzeltin.")
        else:
            # Bakiye Usulü Kalan Boşlukları Tamamlama
            for d_no, info in daire_ozellikleri.items():
                d_toplam_pay = (info["m2"] / toplam_m2) * saf_payda
                mevcut_pay = sum(daire_paylari_dec[d_no].values())
                bos_pay = d_toplam_pay - mevcut_pay

                if bos_pay > 0:
                    for isim, kalan in h_haklar_calisma.items():
                        if isim in daire_ilk_sahipleri[d_no]: continue
                        if kalan > 0:
                            eklenen = min(kalan, bos_pay)
                            daire_paylari_dec[d_no][isim] = daire_paylari_dec[d_no].get(isim, Decimal('0')) + eklenen
                            h_haklar_calisma[isim] -= eklenen
                            bos_pay -= eklenen
                        if bos_pay <= 0: break

            # 3. CRITICAL ADIM: VİRGÜLDEN SONRA KALAN RAKAMLARI BULMA VE DİNAMİK BÜYÜTME
            max_basamak = 0
            # Tüm dairelerdeki payların virgülden sonra kaç basamağı olduğunu kontrol ediyoruz
            for d_no, malikler in daire_paylari_dec.items():
                for malik, pay in malikler.items():
                    max_basamak = max(max_basamak, ondalik_basamak_sayisi(pay))

            # Dinamik Genişletme Çarpanı (Virgülden sonra kaç rakam varsa 10'un o kuvvetiyle çarpıyoruz)
            genisletme_carpani = Decimal(str(10 ** max_basamak))

            # Artık nihai payda ve paylar kesin olarak tam sayıya yükseltildi!
            nihai_payda = int(saf_payda * genisletme_carpani)

            # 4. ADIM: NİHAİ CETVEL OLUŞTURMA (Kesinleşmiş Tam Sayılarla)
            final_list = []
            for d_no, info in daire_ozellikleri.items():
                # Her bir malikin payını tam sayıya dönüştürüyoruz
                malikler_int = {k: int(v * genisletme_carpani) for k, v in daire_paylari_dec[d_no].items() if v > 0}
                hissedar_sayisi = len(malikler_int)
                daire_ici_toplam_pay = sum(malikler_int.values())

                first_row = True
                for malik, pay in malikler_int.items():
                    if hissedar_sayisi == 1:
                        daire_ici_hisse = "Tam"
                    else:
                        daire_ici_hisse = f"{pay} / {daire_ici_toplam_pay}"

                    final_list.append({
                        "Blok Adı": info["blok"] if first_row else "",
                        "Bulunduğu Kat": info["kat"] if first_row else "",
                        "B.B. No": d_no if first_row else "",
                        "Niteliği": info["nitelik"] if first_row else "",
                        "B.B. m2": float(info["m2"]) if first_row else "",
                        "B.B. Toplam Pay": f"{daire_ici_toplam_pay} / {nihai_payda}" if first_row else "",
                        "Malik": malik,
                        "Daire İçi Hisse": daire_ici_hisse,
                        "Genel Arsa Payı": f"{pay} / {nihai_payda}"
                    })
                    first_row = False

            st.subheader("📋 Resmi Arsa Payı Cetveli")
            st.table(pd.DataFrame(final_list))

            # Tam Sıfır Kontrolü
            hatali_bakiye = False
            for isim, bakiye in h_haklar_calisma.items():
                if bakiye != 0:
                    st.error(f"❌ DAĞITIM HATASI: Kalan bakiye tam sıfır değil!")
                    hatali_bakiye = True

            if not hatali_bakiye:
                if max_basamak > 0:
                    st.success(
                        f"🎯 DİNAMİK ÖLÇEKLENDİRME BAŞARILI: Paylarda virgülden sonra en fazla **{max_basamak} basamak** küsurat tespit edildi. Veri kaybını önlemek için tüm arsa payı tabanı otomatik olarak **{int(genisletme_carpani)}** katına büyütülerek tüm değerler resmi kurallara uygun tam sayılara dönüştürüldü.")
                else:
                    st.success(
                        "🎯 MÜKEMMEL UYUM: Hesaplamalarda hiç küsurat oluşmadı, paylar doğrudan tam sayı olarak dağıtıldı.")