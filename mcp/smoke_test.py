#!/usr/bin/env python3
"""
Smoke test for mcp/server.py. Spawns the server over stdio and checks the protocol
and every core tool. Stdlib only. Exit code 0 on success.

    python3 mcp/smoke_test.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "scripts"))


class Client:
    def __init__(self):
        self.p = subprocess.Popen([sys.executable, str(HERE / "server.py")], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(REPO))
        self.next_id = 0

    def send(self, obj):
        self.p.stdin.write((json.dumps(obj) + "\n").encode())
        self.p.stdin.flush()

    def recv(self):
        line = self.p.stdout.readline()
        if not line:
            err = self.p.stderr.read().decode(errors="replace")
            raise AssertionError(f"server closed stdout. stderr:\n{err}")
        return json.loads(line)

    def request(self, method, params=None):
        self.next_id += 1
        msg = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        if params is not None:
            msg["params"] = params
        self.send(msg)
        reply = self.recv()
        assert reply.get("id") == self.next_id, reply
        return reply

    def call(self, name, args):
        r = self.request("tools/call", {"name": name, "arguments": args})
        assert "result" in r, r
        text = r["result"]["content"][0]["text"]
        return r["result"], text

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=10)


def check(cond, label):
    if not cond:
        raise AssertionError(label)
    print(f"ok   {label}")


def main() -> int:
    import sa_id

    c = Client()
    try:
        r = c.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "smoke", "version": "0"}})
        res = r["result"]
        check(res["protocolVersion"] == "2025-06-18", "initialize echoes protocol version")
        check("tools" in res["capabilities"] and "resources" in res["capabilities"], "capabilities tools+resources")
        c.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

        check(c.request("ping")["result"] == {}, "ping")

        tools = {t["name"]: t for t in c.request("tools/list")["result"]["tools"]}
        expected = {"popia_scan", "popia_scan_snippet", "popia_operators", "popia_site_check", "popia_generate_pack",
                    "popia_validate_sa_id", "popia_lookup", "popia_checklist", "popia_breach_triage"}
        check(expected <= set(tools), f"tools/list has {len(expected)} tools")
        check(all("inputSchema" in t for t in tools.values()), "every tool has inputSchema")

        fake = sa_id.fake(1, seed=7)[0]
        result, text = c.call("popia_validate_sa_id", {"id_number": fake})
        body = json.loads(text.split("\n\n---\n")[0])
        check(body == {"valid": True, "masked": sa_id.mask(fake)}, "validate_sa_id returns valid + masked only")
        check(fake not in text, "validate_sa_id never echoes the full ID")
        check("not legal advice" in text, "disclaimer appended")

        _, text = c.call("popia_validate_sa_id", {"id_number": "1234567890123"})
        check('"valid": false' in text, "validate_sa_id rejects a bad ID")

        _, text = c.call("popia_lookup", {"query": "direct marketing"})
        check("Source: references/05-direct-marketing.md" in text, "lookup finds direct marketing reference")

        _, text = c.call("popia_checklist", {"area": "breach"})
        check("BR-01" in text and "BR-08" in text, "checklist breach has BR-01..BR-08")
        _, text = c.call("popia_checklist", {"area": "all"})
        check("ACC-01" in text and "DM-01" in text and "XB-01" in text, "checklist all spans references")

        _, text = c.call("popia_breach_triage", {"description": "RLS was off on the leads table, ID numbers exposed"})
        check("eServices" in text and "[x]" in text and "Hour 0 to 4" in text, "breach triage pre-fills checklist")

        target = REPO / "tests" / "fixtures"
        if not target.is_dir():
            target = REPO / "scripts"
        result, text = c.call("popia_scan", {"path": str(target), "format": "json"})
        check(not result["isError"], f"popia_scan ran on {target.relative_to(REPO)}")
        scan = json.loads(text.split("\n\n---\n")[0])
        check(scan["tool"] == "popia_scan" and "summary" in scan, "popia_scan JSON shape")

        result, text = c.call("popia_operators", {"path": str(target), "format": "json"})
        check(not result["isError"], "popia_operators ran")
        inv = json.loads(text.split("\n\n---\n")[0])
        check(inv["tool"] == "popia_operators" and "operators" in inv, "popia_operators JSON shape")

        snippet = 'const k = "sk_live_' + "a1B2c3D4e5F6g7H8i9J0kLmN" + '";\n'
        result, text = c.call("popia_scan_snippet", {"filename": "src/pay.ts", "content": snippet, "format": "json"})
        scan = json.loads(text.split("\n\n---\n")[0])
        check(scan["target"] == "snippet:src/pay.ts", "scan_snippet target label")
        check("a1B2c3D4e5F6g7H8i9J0kLmN" not in text, "scan_snippet does not echo the secret")

        r = c.request("tools/call", {"name": "popia_scan_snippet", "arguments": {"filename": "../x.ts", "content": ""}})
        check("error" in r and r["error"]["code"] == -32602, "scan_snippet rejects path traversal")

        res = c.request("resources/list")["result"]["resources"]
        uris = {x["uri"] for x in res}
        check("popia://references/07-breach-response.md" in uris, "resources/list includes references")
        r = c.request("resources/read", {"uri": "popia://references/07-breach-response.md"})
        check("s22" in r["result"]["contents"][0]["text"], "resources/read returns content")
        r = c.request("resources/read", {"uri": "popia://../SKILL.md"})
        check("error" in r, "resources/read rejects unknown uri")

        check(c.request("no/such")["error"]["code"] == -32601, "unknown method -> -32601")
        r = c.request("tools/call", {"name": "nope", "arguments": {}})
        check(r["error"]["code"] == -32602, "unknown tool -> -32602")

        c.p.stdin.write(b"{not json\n")
        c.p.stdin.flush()
        check(c.recv()["error"]["code"] == -32700, "malformed JSON -> -32700")
    finally:
        c.close()
    print("smoke test passed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print(f"FAIL {e}", file=sys.stderr)
        sys.exit(1)
