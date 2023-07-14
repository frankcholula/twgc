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
placeholder = st.empty()
data_load_state = st.text("Loading data...")
STAT_P_126_DATA = "data/stat_p_126.csv"
STAT_P_126_METADATA = "data/STAT_P_126_Metadata.csv"


@st.cache_data(ttl=60)
def load_data(filepath: str, nrows=1000) -> pd.DataFrame:
    data = pd.read_csv(filepath, nrows=nrows)
    return data


def extract_metadata(df: pd.DataFrame) -> str:
    pattern = r"\(([\u4e00-\u9fff]+)\)"
    headers = metadata["主要資料欄位"]
    headers = headers.str.findall(pattern).tolist()[0]
    return headers


data = load_data(STAT_P_126_DATA)
metadata = load_data(STAT_P_126_METADATA)
metadata_headers = extract_metadata(metadata)
data_load_state.text("Loading data...done!")


def get_cleaned_compost_data(data: pd.DataFrame) -> pd.DataFrame:
    mask = data["item1"].apply(lambda chinese_date: "月" in chinese_date)
    data = data[mask]

    def _convert_date_regex(chinese_date):
        # Extract the year and month from the Chinese date using regex
        match = re.match(r"(\d+)年\s*(\d*)月*", chinese_date)

        if match:
            # The year is offset by 1911 because the original data is in the Republic of China calendar
            year = int(match.group(1)) + 1911
            month = match.group(2)
            # Convert the year and month to a datetime object
            return pd.to_datetime(f"{year}-{int(month)}")
        else:
            print(f"Problematic input: {chinese_date}")
            return None

    def _rename_columns(df: pd.DataFrame) -> pd.DataFrame:
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

    data = _rename_columns(data)
    data["日期"] = data["統計期"].apply(_convert_date_regex)
    data = data.drop(columns=["統計期"])
    data["廚餘量"] = pd.to_numeric(data["廚餘量"], errors="coerce")
    data = data.dropna()
    return data


cleaned_data = get_cleaned_compost_data(data)

# compost data by months
cdbm = cleaned_data.copy()
cdbm.set_index("日期", inplace=True)
cdbm = cdbm["廚餘量"].resample("MS").asfreq()
cdbm = cdbm.reset_index()
cdbm["月"] = cdbm["日期"].dt.month
cdbm_means = cdbm.groupby("月")["廚餘量"].mean()
avg_dwpp = cleaned_data.copy()

# getting average waste per person
latest_date = avg_dwpp["日期"].max()
prev_latest_date = avg_dwpp["日期"].nlargest(2).iloc[-1]
latest_avg_dwpp = avg_dwpp.loc[avg_dwpp["日期"] == latest_date, "平均每人每日一般廢棄物產生量"].values[
    0
]
prev_avg_dwpp = avg_dwpp.loc[
    avg_dwpp["日期"] == prev_latest_date, "平均每人每日一般廢棄物產生量"
].values[0]

# simulating live data by segmenting the data into yearly chunk
segmented_data = cleaned_data.copy()
segmented_data.sort_values(by="日期", ascending=True, inplace=True)
num_years = 12
partitioned = np.array_split(segmented_data, num_years)
# print(partitioned[0].size)
segments = [partitioned[0]]
# simulating live data
for i in range(num_years - 1):
    old_segments = segments[i]
    new_segment = partitioned[i + 1]
    segments.append(pd.concat([old_segments, new_segment]))

for year in range(11):
    segmented_data["總廚餘量"] = segments[year]["廚餘量"]
    time.sleep(1)

    with placeholder.container():
        st.title("🚚 Taiwan Waste Management Data")
        st.markdown("# 全國一般廢棄物產生量")
        data_description_zh = metadata["資料集描述"].to_string(index=False, header=False)
        data_description_en = "This dashboard consolidates comprehensive waste and recycling data from the Environmental Protection Administration of the Executive Yuan and local environmental protection agencies. It presents statistics on the generation of different waste types and provides insights into the average daily waste generated per person. The unit for the average daily waste per person is kilograms, while the remaining data is measured in metric tons."
        st.write(data_description_zh)
        st.write(data_description_en)
        kpi1, kpi2, kpi3 = st.columns(3)

        kpi1.metric(
            label="每人每日一般廢棄物產生量(kg) 🗑️",
            value=float(latest_avg_dwpp),
            delta=round(float(latest_avg_dwpp) - float(prev_avg_dwpp), ndigits=3),
        )

        st.markdown("## 廚餘量 Compost Data Over Time")
        st.markdown("## ")
        st.line_chart(data=segmented_data, x="日期", y="總廚餘量")

        st.markdown("## 每月平均廚餘量 Compost Data by Months")
        st.bar_chart(cdbm_means, x=cdbm_means.index.all(), y="廚餘量")
        fig3, fig4 = st.columns(2)
        with fig3:
            st.markdown("## Raw data")
            st.write(data)
        with fig4:
            st.markdown("## Cleaned data")
            st.write(cleaned_data)
