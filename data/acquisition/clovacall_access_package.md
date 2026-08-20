# ClovaCall Access Package

## Source

- GitHub: https://github.com/clovaai/ClovaCall
- Paper: https://arxiv.org/abs/2004.09367
- Application form: linked from the GitHub README.

## Use In This Project

ClovaCall is not dialect data. It is a Korean call/contact-center-style ASR baseline corpus.

Use it for:

- call-channel baseline behavior.
- restaurant reservation intent/slot seed examples.
- comparison with AI-Hub clean dialect speech.

Do not use it to claim Busan dialect coverage unless metadata proves regional speaker information, which is not public in the README.

## License Constraints From README

The README states that the materials are for non-commercial AI research and development only, restrict commercial use, restrict modification/editing/reproduction, prohibit third-party redistribution, and require source attribution to NAVER Corp.

Implication:

- Do not commit audio or derived modified audio.
- Treat telephone augmentation experiments on ClovaCall as legally sensitive until license permission is clarified.
- Use AI-Hub dialect data for augmentation experiments first if AI-Hub terms allow derived processing.

## Acquisition Steps

1. Submit the ClovaCall application form from the README.
2. Save approval email or terms under a private local-only folder, not git.
3. Place downloaded files under:

```text
data/raw/clovacall/
```

4. Generate a local manifest only:

```text
data/interim/manifests/clovacall_manifest.local.jsonl
```

The `.local` suffix means it must not be committed if it contains speaker/audio paths from restricted data.
