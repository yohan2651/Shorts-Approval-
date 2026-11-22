import os, requests, json
tok=os.environ["GITHUB_TOKEN"]
H={"Authorization":f"Bearer {tok}","Content-Type":"application/json","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
def show(label, r): print(label, r.status_code, r.headers.get("content-type"), repr(r.text[:300]), flush=True)
show("catalog", requests.get("https://models.github.ai/catalog/models", headers=H, timeout=60))
for model in ["openai/gpt-4.1-mini","openai/gpt-4o-mini","openai/gpt-4.1"]:
    show(f"minimal {model}", requests.post("https://models.github.ai/inference/chat/completions", headers=H, json={"model":model,"messages":[{"role":"user","content":"Say hi"}]}, timeout=60))
show("data= body", requests.post("https://models.github.ai/inference/chat/completions", headers=H, data=json.dumps({"model":"openai/gpt-4.1-mini","messages":[{"role":"user","content":"Say hi"}]}), timeout=60))
show("user api", requests.get("https://api.github.com/rate_limit", headers=H, timeout=60))
