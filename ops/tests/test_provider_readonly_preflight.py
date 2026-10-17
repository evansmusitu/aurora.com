import importlib.util,io,json,pathlib,subprocess,unittest
p=pathlib.Path(__file__).resolve().parents[1]/"provider_readonly_preflight.py"
sp=importlib.util.spec_from_file_location("provider_readonly_preflight",p)
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
class FakeResponse:
    def __init__(self,obj):self.data=io.BytesIO(json.dumps(obj).encode())
    def __enter__(self):return self.data
    def __exit__(self,*args):pass
class ProviderPreflight(unittest.TestCase):
    def test_no_credentials_means_no_deployment(self):
        x=m.inspect({})
        self.assertFalse(x["render_authorized"])
        self.assertFalse(x["deployment_authorized"])
        self.assertFalse(x["provider_zero_charge_cap_verified"])
        self.assertEqual(x["cloudflare"]["status"],"NOT_CONFIGURED")
    def test_reads_only_known_cloudflare_resources(self):
        paths=[]
        def opener(req,timeout):
            self.assertEqual(req.get_method(),"GET")
            paths.append(req.full_url)
            if req.full_url.endswith("/accounts/"+"a"*32):
                return FakeResponse({"success":True,"result":{"id":"a"*32}})
            if "/d1/" in req.full_url:
                return FakeResponse({"success":True,"result":[{"name":"musitu-studio-v02"}]})
            if "/r2/" in req.full_url:
                return FakeResponse({"success":True,"result":{"buckets":[]}})
            raise AssertionError("Unexpected endpoint")
        x=m.inspect({"STUDIO_CF_ACCOUNT_ID":"a"*32,"CLOUDFLARE_EMAIL":"x@e.com",
                     "CLOUDFLARE_GLOBAL_API_KEY":"DO_NOT_LOG"},opener=opener)
        self.assertEqual(len(paths),3)
        self.assertEqual(x["cloudflare"]["status"],"READ_ONLY_OK")
        self.assertTrue(x["cloudflare"]["studio_d1_exists"])
        self.assertFalse(x["cloudflare"]["studio_r2_exists"])
        self.assertNotIn("DO_NOT_LOG",json.dumps(x))
        self.assertFalse(x["provider_zero_charge_cap_verified"])
    def test_modal_list_does_not_dispatch(self):
        observed=[]
        def runner(args,**kw):
            observed.append(args)
            return subprocess.CompletedProcess(args,0,'[{"name":"musitu-studio-v02"}]','')
        x=m.inspect({"MODAL_TOKEN_ID":"id","MODAL_TOKEN_SECRET":"DO_NOT_LOG"},
                    run=runner,which=lambda _: "/usr/local/bin/modal")
        self.assertEqual(observed,[["/usr/local/bin/modal","app","list","--json"]])
        self.assertTrue(x["modal"]["studio_app_exists"])
        self.assertFalse(x["render_authorized"])
        self.assertNotIn("DO_NOT_LOG",json.dumps(x))
if __name__=="__main__":unittest.main()
