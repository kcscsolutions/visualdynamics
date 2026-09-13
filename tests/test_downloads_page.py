"""The launch site's preview hands out what this machine built.

`packaging/stage_downloads.py` hardlinks the installers in `dist/`
into `web/launch/downloads/` (gitignored, cleared before any deploy)
and writes `manifest.json` beside them **in the GitHub releases API's
own shape** — so `downloads.html` fills its three slots with one
routine whether the source is the staged manifest (localhost) or the
released assets (deployed).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..',
                                'packaging'))

from stage_downloads import manifest_for, version_of


def test_the_manifest_speaks_the_releases_apis_shape():
    manifest = manifest_for([
        ('VisualDynamics-0.0.1-windows-x64-setup.exe', 261 * 2**20),
        ('VisualDynamics-0.0.1.dmg', 415 * 2**20)])
    assert manifest['local'] is True
    names = [a['name'] for a in manifest['assets']]
    assert names == sorted(names), 'stable order, whatever dist listed'
    windows = next(a for a in manifest['assets']
                   if a['name'].endswith('setup.exe'))
    # the keys the page reads off a GitHub release asset, exactly
    assert windows['browser_download_url'] \
        == 'downloads/VisualDynamics-0.0.1-windows-x64-setup.exe'
    assert windows['size'] == 261 * 2**20


def test_nothing_staged_is_an_empty_manifest_not_a_missing_one():
    manifest = manifest_for([])
    assert manifest['assets'] == [], (
        'the page falls back to the releases API on an empty list')


def test_the_page_asks_for_the_manifest_only_locally():
    """The deployed page must never request a file that only exists on
    a development machine — the guard is the hostname check."""
    import pathlib

    page = pathlib.Path(os.path.dirname(__file__), '..', 'web', 'launch',
                        'downloads.html').read_text(encoding='utf-8')
    assert "fetch('downloads/manifest.json')" in page
    assert "here === 'localhost' || here === '127.0.0.1'" in page
    assert page.index("localhost") < page.index(
        "fetch('downloads/manifest.json')"), (
        'the hostname gate reads before the fetch it guards')


def test_the_site_job_deploys_the_directory_the_docs_build_into():
    """One deploy carries the launch pages, the documentation and the
    update manifest (Brandon, 2026-09-01). That holds only while the
    workflow deploys the directory mkdocs builds into, and only while
    the job runs on a *published* release — a tag whose release is
    still a draft must not put a manifest in front of the update
    check that names assets nobody can download yet."""
    import os

    import yaml

    root = os.path.join(os.path.dirname(__file__), '..')
    with open(os.path.join(root, '.github', 'workflows', 'release.yml'),
              encoding='utf-8') as handle:
        workflow = yaml.safe_load(handle)
    with open(os.path.join(root, 'properdocs.yml'), encoding='utf-8') as handle:
        docs = yaml.safe_load(handle)
    assert workflow[True]['release'] == {'types': ['published']}
    site = workflow['jobs']['site']
    assert site['if'] == "github.event_name == 'release'"
    deploy = [step['run'] for step in site['steps'] if 'wrangler' in step.get('run', '')]
    assert len(deploy) == 1
    deployed = deploy[0].split('pages deploy ')[1].split()[0]
    assert docs['site_dir'].startswith(deployed + '/'), (
        f'mkdocs builds into {docs["site_dir"]}, the job deploys {deployed}')
    manifest = [step for step in site['steps'] if 'latest.json' in step.get('run', '')]
    assert manifest and f"{deployed}/latest.json" in manifest[0]['run']
    for name in ('linux', 'windows'):
        assert "github.event_name != 'release'" in workflow['jobs'][name]['if'], (
            f'{name} would rebuild on every publish')


def test_the_manifest_is_one_release_the_newest():
    """Staging is cumulative, so two versions can sit in the folder;
    the page takes the first file matching a platform, and a
    name-sorted list handed out 0.0.1 ahead of 0.1.0 — the old,
    unsigned image, the evening the notarised one landed (Brandon,
    2026-09-02). A manifest is one release: the newest version's
    files, and nothing older."""
    manifest = manifest_for([
        ('VisualDynamics-0.0.1-macos-arm64.dmg', 10),
        ('VisualDynamics-0.1.0-macos-arm64.dmg', 11),
        ('VisualDynamics-0.1.0-windows-x64-setup.exe', 12),
        ('VisualDynamics-0.0.1-windows-x64-setup.exe', 9)])
    names = [a['name'] for a in manifest['assets']]
    assert names == ['VisualDynamics-0.1.0-macos-arm64.dmg',
                     'VisualDynamics-0.1.0-windows-x64-setup.exe']
    assert manifest['tag_name'] == 'v0.1.0'
    # ten sorts after nine: versions compare as numbers, not text
    later = manifest_for([('VisualDynamics-0.9.0-macos-arm64.dmg', 1),
                          ('VisualDynamics-0.10.0-macos-arm64.dmg', 2)])
    assert [a['name'] for a in later['assets']] == [
        'VisualDynamics-0.10.0-macos-arm64.dmg']


def test_the_pypi_jobs_publish_by_identity_and_only_when_meant():
    """`pip install visualdynamics` on the downloads page is a promise
    the release workflow keeps: the real distribution goes up when the
    release is published, by trusted publishing (id-token, no secret),
    and a hand-run `reserve` holds the name with an empty placeholder
    — without starting the Linux and Windows builds (2026-09-03)."""
    import os

    import yaml

    root = os.path.join(os.path.dirname(__file__), '..')
    with open(os.path.join(root, '.github', 'workflows', 'release.yml'),
              encoding='utf-8') as handle:
        workflow = yaml.safe_load(handle)
    jobs = workflow['jobs']
    for name in ('pypi', 'reserve'):
        job = jobs[name]
        assert job['environment'] == 'pypi'
        assert job['permissions'] == {'id-token': 'write'}, 'trusted publishing'
        publish = [s for s in job['steps'] if 'pypi-publish' in s.get('uses', '')]
        assert len(publish) == 1
        assert not any('password' in s.get('with', {}) for s in job['steps'])
    assert jobs['pypi']['if'] == "github.event_name == 'release'"
    assert 'inputs.reserve' in jobs['reserve']['if']
    for name in ('linux', 'windows'):
        assert '!inputs.reserve' in jobs[name]['if'], (
            f'{name} would build on a reserve run')
    assert workflow[True]['workflow_dispatch']['inputs']['reserve']['default'] is False


def test_the_release_publishes_checksums_for_every_asset():
    """The downloads page promises notes and checksums (2026-09-11): the
    publish job writes SHA256SUMS over the runner builds before the
    draft opens, and the day-of script that attaches the two desk-built
    macOS images adds their lines to the same file."""
    import pathlib

    import yaml

    ROOT = pathlib.Path(__file__).resolve().parent.parent
    workflow = yaml.safe_load(
        (ROOT / '.github' / 'workflows' / 'release.yml').read_text(encoding='utf-8'))
    steps = workflow['jobs']['publish']['steps']
    checksums = [s for s in steps if s.get('name') == 'Checksums']
    assert len(checksums) == 1 and 'sha256sum * > SHA256SUMS' in checksums[0]['run']
    upload = next(i for i, s in enumerate(steps) if 'gh-release' in s.get('uses', ''))
    assert steps.index(checksums[0]) < upload, 'summed before the assets are attached'
    script = ROOT / 'packaging' / 'attach_macos.sh'
    assert os.access(script, os.X_OK)
    text = script.read_text(encoding='utf-8')
    assert 'SHA256SUMS' in text and '--clobber' in text and 'stapler validate' in text
    page = (ROOT / 'web' / 'launch' / 'downloads.html').read_text(encoding='utf-8')
    assert 'shasum -a 256 -c SHA256SUMS' in page


def test_the_staging_parser_agrees_with_the_update_check():
    """`stage_downloads.version_of` is a deliberate second parser — the
    script runs under the system python and cannot import the package
    — so the two are held to one answer here, alpha and release alike."""
    from visualdynamics.update import parse_version

    for text in ('0.1.0', '0.1.0a1', '0.2.0b3', '1.0.0rc1', '0.10.2'):
        assert version_of(f'VisualDynamics-{text}-macos-arm64.dmg') == \
            parse_version(text), text
