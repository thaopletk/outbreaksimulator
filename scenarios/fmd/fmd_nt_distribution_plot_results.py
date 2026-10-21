import FMD_functions
import datetime
import pandas as pd
import os
import matplotlib.pyplot as plt

state = "NT"
main_folder_name = "NT_test"
start_year = 2026
start_month = 7
start_day = 1
wind_radius = 20
start_date = datetime.datetime(year=start_year, month=start_month, day=start_day)


data_file = os.path.join(os.path.dirname(__file__), main_folder_name, "06_large_vs_small_CAs_two_weeks.csv")
data_df = pd.read_csv(data_file)

# data_file2 = os.path.join(os.path.dirname(__file__), main_folder_name, "06_large_vs_small_CAs.csv")
# data_df2 = pd.read_csv(data_file2)

# data_file3 = os.path.join(os.path.dirname(__file__), main_folder_name, "06_large_vs_small_CAs_3.csv")
# data_df3 = pd.read_csv(data_file3)

# data_df = pd.concat([data_df, data_df2, data_df3], axis=0, ignore_index=True)


# header = [
#     "run_id",
#     "strategy",
#     "infected_properties_with_infected_animals",
#     "confirmed_IPs",
#     "undetected_properties_with_infected_animals",
#     "infected_properties_with_infected_animals_or_depop",
#     "labtests",
# ]


fig, (ax1, ax2, ax3) = plt.subplots(3, tight_layout=True)

counts = data_df[data_df["strategy"] == "large_CA"]["infected_properties_with_infected_animals_or_depop"].value_counts()
ax1.bar(counts.index.values.tolist(), counts.to_list(), label="large CAs", alpha=0.5, color="#10B3FF", width=1, edgecolor="blue")


counts = data_df[data_df["strategy"] == "small_CA"]["infected_properties_with_infected_animals_or_depop"].value_counts()
ax1.bar(counts.index.values.tolist(), counts.to_list(), label="small CAs", alpha=0.5, color="#F16565", width=1, edgecolor="#C73939")


ax1.set_title("Total IPs and undetected infected properties")

ax1.legend()

# ############
counts = data_df[data_df["strategy"] == "large_CA"]["confirmed_IPs"].value_counts()
ax2.bar(counts.index.values.tolist(), counts.to_list(), label="large CAs", alpha=0.5, color="#10B3FF", width=1, edgecolor="blue")

counts = data_df[data_df["strategy"] == "small_CA"]["confirmed_IPs"].value_counts()
ax2.bar(counts.index.values.tolist(), counts.to_list(), label="small CAs", alpha=0.5, color="#F16565", width=1, edgecolor="#C73939")


ax2.set_title("Confirmed IPs")

ax2.legend()

##############

counts = data_df[data_df["strategy"] == "large_CA"]["undetected_properties_with_infected_animals"].value_counts()
ax3.bar(counts.index.values.tolist(), counts.to_list(), label="large CAs", alpha=0.5, color="#10B3FF", width=1, edgecolor="blue")

counts = data_df[data_df["strategy"] == "small_CA"]["undetected_properties_with_infected_animals"].value_counts()
ax3.bar(counts.index.values.tolist(), counts.to_list(), label="small CAs", alpha=0.5, color="#F16565", width=1, edgecolor="#C73939")


ax3.set_title("Undetected IPs")

ax3.legend()


plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(__file__), main_folder_name, "06_large_vs_small_CAs_two_weeks.png"), bbox_inches="tight")
plt.close()


# labtests
