# AI-Hub Filekeys

Observed through local `aihubshell -mode l` on 2026-08-11 KST.

## Disk Status

Local available space at probe time: 21 GiB.

Do not download any 28 GB source-audio archive to this disk. AI-Hub recommends 2-3x archive size during merge/unzip, so a 28 GB file can require far more than the current free space.

Rechecked after cleanup on 2026-08-11 KST: local available space was about 36 GiB. This is still below the project guard of 90 GB for filekey `572714`.

## Dataset 119: 한국어 방언 발화 데이터(경상도)

| Split | Type | File | Size | filekey | Pilot priority |
| --- | --- | --- | --- | --- | --- |
| Training | Label | `(비식별화완료)경상도_학습데이터_1.zip` | 308 MB | `572701` | second |
| Training | Source audio | `(비식별화완료)경상도_1.zip` | 28 GB | `572702` | blocked by disk |
| Training | Source audio | `(비식별화완료)경상도_10.zip` | 27 GB | `572703` | blocked by disk |
| Training | Source audio | `(비식별화완료)경상도_11.zip` | 28 GB | `572704` | blocked by disk |
| Training | Source audio | `(비식별화완료)경상도_12.zip` | 27 GB | `572705` | blocked by disk |
| Training | Source audio | `(비식별화완료)경상도_3.zip` | 28 GB | `572706` | blocked by disk |
| Training | Source audio | `(비식별화완료)경상도_4.zip` | 27 GB | `572707` | blocked by disk |
| Training | Source audio | `(비식별화완료)경상도_5.zip` | 27 GB | `572708` | blocked by disk |
| Training | Source audio | `(비식별화완료)경상도_6.zip` | 27 GB | `572709` | blocked by disk |
| Training | Source audio | `(비식별화완료)경상도_7.zip` | 27 GB | `572710` | blocked by disk |
| Training | Source audio | `(비식별화완료)경상도_9.zip` | 27 GB | `572711` | blocked by disk |
| Training add | Source audio | `(비식별화완료)경상도_8.zip` | 17 GB | `572712` | risky on current disk |
| Validation | Label | `(비식별화완료)경상도_학습데이터_2.zip` | 32 MB | `572713` | first |
| Validation | Source audio | `(비식별화완료)경상도_2.zip` | 28 GB | `572714` | downloaded locally |

## Dataset 71517: 중·노년층 한국어 방언 데이터(강원도, 경상도)

| Split | Type | File | Size | filekey | Pilot priority |
| --- | --- | --- | --- | --- | --- |
| Training | Label | `TL_02. 경상도_01. 1인발화 따라말하기.zip` | 746 MB | `538313` | later |
| Training | Label | `TL_02. 경상도_02. 1인발화 질문에답하기.zip` | 1 GB | `538314` | later |
| Training | Label | `TL_02. 경상도_03. 2인발화.zip` | 472 MB | `538315` | later |
| Validation | Label | `VL_02. 경상도_01. 1인발화 따라말하기.zip` | 96 MB | `538325` | optional |
| Validation | Label | `VL_02. 경상도_02. 1인발화 질문에답하기.zip` | 167 MB | `538326` | optional |
| Validation | Label | `VL_02. 경상도_03. 2인발화.zip` | 58 MB | `538327` | optional |

Source-audio archives for this dataset range from 2 GB to 41 GB. Do not pull them before freeing storage or selecting an external disk.
