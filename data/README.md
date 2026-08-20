# Data Workspace

Raw speech data is not committed here. AI-Hub and ClovaCall both have access and redistribution constraints.

Use this layout after access approval:

```text
data/
  raw/
    aihub_gyeongsang_119/
    aihub_senior_gangwon_gyeongsang_71517/
    clovacall/
  interim/
    manifests/
    telephone_augmented/
  processed/
    splits/
    annotations/
```

## Access Status

| Dataset | Status | Reason |
| --- | --- | --- |
| AI-Hub 한국어 방언 발화(경상도) | requires approval | AI-Hub download needs login/application; direct curl returns 403. |
| AI-Hub 중·노년층 한국어 방언 데이터(강원도, 경상도) | requires approval | AI-Hub download needs login/application. |
| ClovaCall | requires application | GitHub code/README are public; data application and non-commercial license apply. |

Do not upload or redistribute downloaded audio. Store local paths only in generated manifests.
