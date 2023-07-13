# Define the column names
column_names = ["統計期", "總產生量", "一般垃圾量", "資源回收量", "堆肥量", "回收率"]

# Reload the data with the correct column names
data = pd.read_csv(data_path, names=column_names, skiprows=1)

# Apply the date parsing function to the "統計期" column
data["date"] = data["統計期"].apply(parse_date)

# Drop the original "統計期" column and set "date" as the index
data = data.drop(columns=["統計期"]).set_index("date")

# Display the first few rows of the modified dataset
data.head()