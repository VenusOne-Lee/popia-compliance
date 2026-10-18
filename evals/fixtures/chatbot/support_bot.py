# FAKE EVAL FIXTURE. Sends full customer records to a US-hosted LLM.
import json, urllib.request

def answer(question, customer):
    prompt = f"Customer record: {json.dumps(customer)}\nQuestion: {question}"
    body = json.dumps({"model": "some-model", "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.example-llm.com/v1/chat/completions", data=body,
                                 headers={"content-type": "application/json"})
    resp = urllib.request.urlopen(req).read()
    with open("transcripts.log", "a") as f:          # kept forever
        f.write(prompt + "\n" + resp.decode() + "\n")
    return resp

# customer dict contains: name, email, phone, sa_id_number, account_number, order_history, complaints
