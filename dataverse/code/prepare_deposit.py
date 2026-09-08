import pandas as pd

RAW = "data/raw/200_free_scy_raw.csv"
OUT = "dataverse/data/races_200free_scy.csv"
DROP = ["team", "pre_race_pb", "split_15m", "reaction_time"]
SPL = ["split_50", "split_100", "split_150", "split_200"]

df = pd.read_csv(RAW)
df = df.drop(columns=[c for c in DROP if c in df.columns])
df.to_csv(OUT, index=False)

def secs(v):
    if pd.isna(v):
        return None
    s = str(v)
    if ":" in s:
        m, r = s.split(":")
        return int(m) * 60 + float(r)
    return float(s)

print("shape:", df.shape)
print("dates:", df.meet_date.min(), df.meet_date.max())
print(df["round"].value_counts().to_string())
sub = df.dropna(subset=SPL).head(3)
for _, r in sub.iterrows():
    tot = sum(secs(r[c]) for c in SPL)
    print("splits:", [r[c] for c in SPL])
    print("sum:", round(tot, 2), "final:", secs(r.final_time))
