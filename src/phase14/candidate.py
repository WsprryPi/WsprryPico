"""Bind finite host trials to the ordinary identified RF artifact, without devices."""
import hashlib
import json
from pathlib import Path
import re


def candidate(root,clock=138000000):
    root=Path(root);manifest=json.loads((root/'artifacts/manifest.json').read_text())
    if (manifest['schema']!='phase14-candidates/1' or not re.fullmatch('[0-9a-f]{40}',manifest['source_commit']) or
        manifest['board']!='pico2_w' or manifest['engine']!='pio-dma-gp2' or manifest['divider']!=1 or manifest['rf_gp']!=2 or
        manifest['gp14_enabled'] or manifest['fixtures_enabled'] or manifest['release_qualified'] or
        manifest['sdk_commit']!='079c6f39023649b154152db30f1d781e884879bc' or
        manifest['picotool_commit']!='6f6458d792b93685a11423b244a585eaa99eafcf'):
        raise ValueError('identified ordinary unqualified candidate required')
    image=manifest['images'][str(clock)]['uf2'];path=root/'artifacts'/Path(image['path']).name
    with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    if digest!=image['sha256']:raise ValueError('candidate artifact substitution')
    from check_standalone_image import validate_uf2
    validate_uf2(path.read_bytes())
    return manifest,image,path
