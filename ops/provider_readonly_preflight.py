"""MUSITU Studio stage-zero provider inspection. GET/list ONLY; no writes, compute or billing changes."""
import json, os, pathlib, re, shutil, subprocess, urllib.error, urllib.request
def inspect(env, opener=urllib.request.urlopen, run=subprocess.run, which=shutil.which):
    result={"schema":"musitu.studio.readonly-preflight.v1","read_only":True,
      "render_authorized":False,"deployment_authorized":False,"provider_zero_charge_cap_verified":False,
      "cloudflare":{"status":"NOT_CONFIGURED"},"modal":{"status":"NOT_CONFIGURED"}}
    aid=env.get("STUDIO_CF_ACCOUNT_ID","")
    if (re.fullmatch("[0-9a-fA-F]{32}",aid) and env.get("CLOUDFLARE_EMAIL")
        and env.get("CLOUDFLARE_GLOBAL_API_KEY")):
        headers={"X-Auth-Email":env["CLOUDFLARE_EMAIL"],
                 "X-Auth-Key":env["CLOUDFLARE_GLOBAL_API_KEY"],"Accept":"application/json"}
        def get(path):
            req=urllib.request.Request("https://api.cloudflare.com/client/v4"+path,headers=headers,method="GET")
            with opener(req,timeout=25) as resp: payload=json.load(resp)
            if not payload.get("success"):raise ValueError("CLOUDFLARE_REJECTED")
            return payload["result"]
        try:
            account=get("/accounts/"+aid.lower())
            if account.get("id","").lower()!=aid.lower():raise ValueError("WRONG_ACCOUNT")
            d1=get("/accounts/"+aid.lower()+"/d1/database?per_page=100")
            r2=get("/accounts/"+aid.lower()+"/r2/buckets?per_page=100")
            buckets=r2.get("buckets",[]) if isinstance(r2,dict) else r2
            result["cloudflare"]={"status":"READ_ONLY_OK","account_verified":True,
              "studio_d1_exists":any(x.get("name")=="musitu-studio-v02" for x in d1 or []),
              "studio_r2_exists":any(x.get("name")=="musitu-studio-v02-assets" for x in buckets or [])}
        except (OSError,ValueError,KeyError,TypeError,urllib.error.URLError):
            result["cloudflare"]={"status":"CANNOT_VERIFY"}
    if env.get("MODAL_TOKEN_ID") and env.get("MODAL_TOKEN_SECRET"):
        binary=which("modal")
        if not binary:result["modal"]={"status":"CLI_NOT_INSTALLED"}
        else:
            try:
                r=run([binary,"app","list","--json"],env=dict(os.environ,**dict(env)),
                      capture_output=True,text=True,timeout=30,check=False)
                if r.returncode:raise ValueError("MODAL_CLI_FAILED")
                body=json.loads(r.stdout)
                apps=body if isinstance(body,list) else body.get("apps",[])
                result["modal"]={"status":"READ_ONLY_OK",
                  "studio_app_exists":any(a.get("name")=="musitu-studio-v02" for a in apps if isinstance(a,dict))}
            except (OSError,ValueError,subprocess.TimeoutExpired):
                result["modal"]={"status":"CANNOT_VERIFY"}
    return result
if __name__=="__main__":
    report=inspect(os.environ)
    pathlib.Path("studio-provider-preflight.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))
