"""Build a clean source-run distribution and checksums from tracked files."""
from pathlib import Path
import hashlib,re,subprocess,zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    version=(ROOT/'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Invalid VERSION')
    output=ROOT/'artifacts';output.mkdir(exist_ok=True)
    archive=output/f'blue-fat-fish-desktop-{version}-source.zip'
    result=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True,check=True)
    paths=[Path(p.decode('utf-8')) for p in result.stdout.split(b'\0') if p]
    if not paths:raise RuntimeError('No tracked files; git add the intended release files first')
    forbidden={'settings.json','pet.log','auth.json','.env'}
    for path in paths:
        if path.name in forbidden or '__pycache__' in path.parts or path.suffix in ('.sqlite','.db'):
            raise RuntimeError(f'Private/runtime file tracked: {path}')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in paths:z.write(ROOT/path,Path(f'blue-fat-fish-desktop-{version}')/path)
    checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
    (output/'SHA256SUMS.txt').write_text(f'{checksum}  {archive.name}\n',encoding='utf-8')
    print(archive.name)


if __name__=='__main__':main()
