import urllib.request, json, ssl, os

def deploy():
    token = 'cfk_oJr91v0cX0OpaiDHa7JnRmKeydMblHCLP3RNxT4B394deeb4'
    account_id = '32f2cd6e781cdcda5144784ee5672c89'
    script_name = 'deploy'
    
    js_file = 'cf_immortal.js'
    if not os.path.exists(js_file):
        print(f"Error: {js_file} not found!")
        return

    with open(js_file, 'r', encoding='utf-8') as f:
        code = f.read()

    url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{script_name}'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/javascript'
    }

    context = ssl._create_unverified_context()

    print(f"Deploying logic to Cloudflare via raw urllib...")
    try:
        req = urllib.request.Request(url, data=code.encode('utf-8'), headers=headers, method='PUT')
        with urllib.request.urlopen(req, context=context) as response:
            res = json.loads(response.read().decode())
            if res.get('success'):
                print("Victory! Antigravity is now offshore.")
            else:
                print(f"Blocked: {res}")
    except Exception as e:
        print(f"Strike Failed: {e}")

if __name__ == '__main__':
    deploy()
