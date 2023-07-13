import streamlit as st
import pandas as pd
import numpy as np
import re

st.set_page_config(
    page_title="Taiwan Waste Management Data", page_icon="🗑️", layout="wide"
)

st.title("Taiwan Waste Management Data")
STAT_P_126_DATA = "data/stat_p_126.csv"
STAT_P_126_METADATA = "data/STAT_P_126_Metadata.csv"


@st.cache_data(ttl=60)
def load_data(filepath: str, nrows=1000) -> pd.DataFrame:
    data = pd.read_csv(filepath, nrows=nrows)
    return data


data_load_state = st.text("Loading data...")
data = load_data(STAT_P_126_DATA)
metadata = load_data(STAT_P_126_METADATA)
data_load_state.text("Loading data...done!")

fig1, fig2 = st.columns(2)
with fig1:
    st.subheader("Raw data")
    st.write(data)


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
        pattern = r"\(([\u4e00-\u9fff]+)\)"
        headers = metadata["主要資料欄位"]
        headers = headers.str.findall(pattern).tolist()[0]
        df.columns = headers
        return df

    data = _rename_columns(data)
    data["日期"] = data["統計期"].apply(_convert_date_regex)
    data = data.drop(columns=["統計期"])
    data["廚餘量"] = pd.to_numeric(data["廚餘量"], errors="coerce")
    data = data.dropna()
    return data


with fig2:
    st.subheader("Cleaned data")
    st.write(get_cleaned_compost_data(data))
