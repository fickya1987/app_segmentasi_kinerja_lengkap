import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt
from io import BytesIO

st.set_page_config(page_title="Segmentasi Kinerja Lengkap", layout="wide")
st.title("📊 Segmentasi Kinerja Pekerja dan Rekomendasi Intervensi")

# Upload file
uploaded_file = st.file_uploader("📥 Upload file `kpi_cleaned.xlsx`", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    df = df.dropna(subset=["NIPP PEKERJA", "TARGET", "REALISASI (%)", "BOBOT (%)", "POLARITAS"]).copy()
    df["TARGET"] = pd.to_numeric(df["TARGET"], errors="coerce")
    df["REALISASI (%)"] = pd.to_numeric(df["REALISASI (%)"], errors="coerce")
    df["BOBOT (%)"] = pd.to_numeric(df["BOBOT (%)"], errors="coerce")

    def hitung_capaian(row):
        t, r, p = row["TARGET"], row["REALISASI (%)"], str(row["POLARITAS"]).strip().lower()
        if t == 0 or (p == "negatif" and r == 0): return 0
        if p == "positif": return (r / t) * 100
        elif p == "negatif": return (t / r) * 100
        else: return 100

    df["CAPAIAN (%)"] = df.apply(hitung_capaian, axis=1)
    df["SKOR TERTIMBANG"] = df["CAPAIAN (%)"] * df["BOBOT (%)"] / 100

    # Agregasi
    df_summary = df.groupby(["NIPP PEKERJA", "POSISI PEKERJA"]).agg({
        "SKOR TERTIMBANG": "sum",
        "BOBOT (%)": "sum"
    }).reset_index()
    df_summary["FINAL SKOR"] = (df_summary["SKOR TERTIMBANG"] / df_summary["BOBOT (%)"]) * 100

    def tentukan_kategori(score):
        if score > 110:
            return "ISTIMEWA"
        elif score > 105:
            return "SANGAT BAIK"
        elif score >= 90:
            return "BAIK"
        elif score >= 80:
            return "CUKUP"
        else:
            return "KURANG"

    df_summary["KATEGORI"] = df_summary["FINAL SKOR"].apply(tentukan_kategori)

    # TABEL
    st.subheader("📋 Tabel Segmentasi Kinerja")
    st.dataframe(df_summary)

    # PIE CHART
    st.subheader("📈 Komposisi Pie Kategori Kinerja")
    kategori_count = df_summary["KATEGORI"].value_counts().sort_index()
    fig, ax = plt.subplots()
    ax.pie(kategori_count, labels=kategori_count.index, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 8})
    ax.axis("equal")
    st.pyplot(fig)

    # BAR CHART
    st.subheader("📊 Grafik Jumlah Pekerja per Kategori")
    bar_chart = alt.Chart(df_summary).mark_bar().encode(
        x=alt.X("KATEGORI:N", sort=["KURANG", "CUKUP", "BAIK", "SANGAT BAIK", "ISTIMEWA"]),
        y=alt.Y("count():Q"),
        tooltip=["count()"],
        color="KATEGORI:N"
    ).properties(width=600)
    st.altair_chart(bar_chart)

    # EKSPOR EXCEL PER KATEGORI
    st.subheader("📤 Unduh Excel per Kategori")
    for kategori in df_summary["KATEGORI"].unique():
        sub_df = df_summary[df_summary["KATEGORI"] == kategori]
        towrite = BytesIO()
        with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
            sub_df.to_excel(writer, index=False, sheet_name="Segmentasi")
        st.download_button(
            label=f"📁 Unduh: {kategori}",
            data=towrite.getvalue(),
            file_name=f"segmentasi_{kategori}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # REKOMENDASI INTERVENSI
    st.subheader("🧠 Rekomendasi Intervensi per Kategori")
    rekomendasi = {
        "ISTIMEWA": "🎖 Dipertahankan, diberi penghargaan, dan dipertimbangkan untuk talent pool.",
        "SANGAT BAIK": "💡 Dipertimbangkan untuk peran lebih tinggi atau pelatihan kepemimpinan.",
        "BAIK": "🔍 Monitoring rutin dan penguatan peran sesuai potensi.",
        "CUKUP": "🛠 Perlu program coaching atau mentoring triwulanan.",
        "KURANG": "⚠ Masuk prioritas untuk Corrective Action (PICA) dan pendampingan intensif."
    }

    for kat, rekom in rekomendasi.items():
        jumlah = kategori_count.get(kat, 0)
        st.markdown(f"**{kat}** – {jumlah} pekerja  
        → _{rekom}_")
