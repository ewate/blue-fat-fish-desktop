"""Publish a tested tag using the workflow's short-lived GitHub token."""
from pathlib import Path
import json,os,re,mimetypes,urllib.request,urllib.error,urllib.parse

ROOT=Path(__file__).resolve().parents[1]


def main():
    token=os.environ['GITHUB_TOKEN']
    repo=os.environ['GITHUB_REPOSITORY']
    version=(ROOT/'VERSION').read_text().strip()
    tag=os.environ['GITHUB_REF_NAME']
    if tag!='v'+version:raise ValueError('Tag does not match VERSION')
    headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'blue-fat-fish-release'}
    def call(method,path,data=None,content_type='application/json'):
        url=path if path.startswith('https://') else 'https://api.github.com'+path
        if isinstance(data,dict):data=json.dumps(data).encode('utf-8')
        h=dict(headers)
        if data is not None:h['Content-Type']=content_type
        with urllib.request.urlopen(urllib.request.Request(url,headers=h,data=data,method=method),timeout=180) as response:
            raw=response.read();return json.loads(raw) if raw else None
    try:
        release=call('GET',f'/repos/{repo}/releases/tags/{tag}')
        if not release['draft']:
            print(release['html_url']);return
    except urllib.error.HTTPError as e:
        if e.code!=404:raise
        notes=(ROOT/'CHANGELOG.md').read_text(encoding='utf-8')
        match=re.search(r'## \['+re.escape(version)+r'\][^\n]*\n(.*?)(?=\n## |\Z)',notes,re.S)
        release=call('POST',f'/repos/{repo}/releases',{'tag_name':tag,'name':'蓝色大肥鱼 '+tag,'body':match.group(1).strip() if match else tag,'draft':True,'prerelease':False})
    existing={asset['name'] for asset in call('GET',f'/repos/{repo}/releases/{release["id"]}/assets')}
    for file in sorted((ROOT/'artifacts').iterdir()):
        if not file.is_file():continue
        if file.name in existing:continue
        url=release['upload_url'].split('{')[0]+'?name='+urllib.parse.quote(file.name)
        call('POST',url,file.read_bytes(),mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
    release=call('PATCH',f'/repos/{repo}/releases/{release["id"]}',{'draft':False,'make_latest':'true'})
    print(release['html_url'])


if __name__=='__main__':main()
