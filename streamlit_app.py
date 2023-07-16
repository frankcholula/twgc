import streamlit as st
import pandas as pd
import numpy as np
import re
import time

# Dashboard setup
pd.set_option("display.max_colwidth", None)
st.set_page_config(
    page_title="Taiwan Waste Management Data",
    page_icon="🗑️",
    layout="centered",
    initial_sidebar_state="auto",
)

DATA_DIR = "data/"
STAT_P_126_DATA = DATA_DIR + "stat_p_126.csv"
STAT_P_126_METADATA = DATA_DIR + "STAT_P_126_Metadata.csv"


@st.cache_data(ttl=60)
def load_data(filepath: str, nrows=1000) -> pd.DataFrame:
    data = pd.read_csv(filepath, nrows=nrows)
    return data


def extract_metadata(df: pd.DataFrame) -> str:
    pattern = r"\(([\u4e00-\u9fff]+)\)"
    headers = metadata["主要資料欄位"]
    headers = headers.str.findall(pattern).tolist()[0]
    return headers


data_load_state = st.text("Loading data...")
data = load_data(STAT_P_126_DATA)
metadata = load_data(STAT_P_126_METADATA)
metadata_headers = extract_metadata(metadata)
data_load_state.text("Loading data...done!")


def get_cleaned_compost_data(data: pd.DataFrame) -> pd.DataFrame:
    mask = data["item1"].str.contains("月")
    data = data[mask]

    def convert_date_regex(chinese_date):
        match = re.match(r"(\d+)年\s*(\d*)月*", chinese_date)
        if match:
            year = int(match.group(1)) + 1911
            month = match.group(2)
            return pd.to_datetime(f"{year}-{int(month)}")
        else:
            print(f"Problematic input: {chinese_date}")
            return None

    def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
        column_mapping = {
            "item1": "統計期",
            "value1": "總產生量",
            "value2": "一般垃圾量",
            "value3": "資源垃圾量",
            "value4": "廚餘量",
            "value5": "平均每人每日一般廢棄物產生量",
        }
        df = df.rename(columns=column_mapping)
        return df

    data = rename_columns(data)
    data["日期"] = data["統計期"].apply(convert_date_regex)
    data = data.drop(columns=["統計期"])
    data["廚餘量"] = pd.to_numeric(data["廚餘量"], errors="coerce")
    data = data.dropna()
    return data


cleaned_data = get_cleaned_compost_data(data)

# Compost data by months
cdbm = cleaned_data.copy()
cdbm.set_index("日期", inplace=True)
cdbm = cdbm["廚餘量"].resample("MS").asfreq()
cdbm = cdbm.reset_index()
cdbm["月"] = cdbm["日期"].dt.month
cdbm_means = cdbm.groupby("月")["廚餘量"].mean()

# Average waste per person
avg_dwpp = cleaned_data.copy()
latest_date = avg_dwpp["日期"].max()
prev_latest_date = avg_dwpp["日期"].nlargest(2).iloc[-1]
latest_avg_dwpp = avg_dwpp.loc[avg_dwpp["日期"] == latest_date, "平均每人每日一般廢棄物產生量"].values[
    0
]
prev_avg_dwpp = avg_dwpp.loc[
    avg_dwpp["日期"] == prev_latest_date, "平均每人每日一般廢棄物產生量"
].values[0]

# Simulating live data by segmenting the data into yearly chunks
segmented_data = cleaned_data.copy()
segmented_data.sort_values(by="日期", ascending=True, inplace=True)
num_years = 12
partitioned = np.array_split(segmented_data, num_years)
segments = [partitioned[0]]
for i in range(num_years - 1):
    old_segments = segments[i]
    new_segment = partitioned[i + 1]
    segments.append(pd.concat([old_segments, new_segment]))

LIVE_DATA = st.checkbox("LIVE DATA")
placeholder = st.empty()

for year in range(11):
    segmented_data["總廚餘量"] = segments[year]["廚餘量"]
    time.sleep(1)

    with placeholder.container():
        st.title("🚚 Taiwan Waste Management Data")
        st.markdown("# 全國一般廢棄物產生量")
        desc_zh = metadata["資料集描述"].to_string(index=False, header=False)
        desc_en = "This dashboard consolidates comprehensive waste and recycling data from the Environmental Protection Administration of the Executive Yuan and local environmental protection agencies. It presents statistics on the generation of different waste types and provides insights into the average daily waste generated per person. The unit for the average daily waste per person is kilograms, while the remaining data is measured in metric tons."
        st.write(desc_zh)
        st.write(desc_en)
        kpi1, kpi2, kpi3 = st.columns(3)

        kpi1.metric(
            label="每人每日一般廢棄物產生量(kg) 🗑️",
            value=float(latest_avg_dwpp),
            delta=round(float(latest_avg_dwpp) - float(prev_avg_dwpp), ndigits=3),
        )

        st.markdown("## 廚餘量 Compost Data Over Time")
        st.markdown("## ")
        if LIVE_DATA:
            st.line_chart(data=segmented_data, x="日期", y="總廚餘量")
        else:
            st.line_chart(data=cleaned_data, x="日期", y="廚餘量")

        st.markdown("## 每月平均廚餘量 Compost Data by Months")
        st.bar_chart(cdbm_means, x=cdbm_means.index.all(), y="廚餘量")
        fig3, fig4 = st.columns(2)
        with fig3:
            st.markdown("## Raw data")
            st.write(data)
        with fig4:
            st.markdown("## Cleaned data")
            st.write(cleaned_data)
