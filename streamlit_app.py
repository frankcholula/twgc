import streamlit as st
import pandas as pd
import numpy as np
import re

# Dashboard setup
pd.set_option("display.max_colwidth", None)
st.set_page_config(
    page_title="Taiwan Waste Management Data", page_icon="🗑️", layout="wide"
)

st.title("🚚 Taiwan Waste Management Data")
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


data_load_state = st.text("Loading data...")
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


data_description = metadata["資料集描述"].to_string(index=False, header=False)
st.write(data_description)
compost_data = get_cleaned_compost_data(data)
st.subheader("Compost Data Over Time 廚餘量")
st.line_chart(data=compost_data, x="日期", y="廚餘量")

# compost data by months
cdbm = compost_data.copy()
cdbm.set_index("日期", inplace=True)
cdbm = cdbm["廚餘量"].resample("MS").asfreq()
cdbm = cdbm.reset_index()
cdbm["月"] = cdbm["日期"].dt.month
cdbm_means = cdbm.groupby("月")["廚餘量"].mean()
print(cdbm_means)
st.subheader("Compost Data by Months 每月平均廚餘量")
st.bar_chart(cdbm_means, x=cdbm_means.index.all(), y="廚餘量")

fig1, fig2 = st.columns(2)
with fig1:
    st.subheader("Raw data")
    st.write(data)
with fig2:
    st.subheader("Cleaned data")
    st.write(compost_data)
