# RAGOps changelog / Lịch sử thay đổi / 変更履歴

## Unreleased

### English

- No unreleased changes.

## [2.0.1] - 2026-08-23

### English

- Republished the unchanged RAGOps 2.0 feature set under a new patch version because PyPI permanently reserves filenames from deleted releases.
- Corrected the Trusted Publishing action reference so GitHub Actions uses the published v1.14.2 container with Core Metadata 2.5 support.

### Tiếng Việt

- Phát hành lại toàn bộ tính năng RAGOps 2.0 dưới patch version mới vì PyPI khóa vĩnh viễn filename của release đã bị xóa.
- Sửa tham chiếu Trusted Publishing để GitHub Actions dùng container v1.14.2 đã phát hành và hỗ trợ Core Metadata 2.5.

### 日本語

- 削除済みリリースのファイル名を PyPI が恒久的に予約するため、RAGOps 2.0 の機能を新しいパッチ版で再公開しました。
- Trusted Publishing の参照を修正し、Core Metadata 2.5 対応の公開済み v1.14.2 コンテナを使用します。

## [2.0.0] - 2026-08-23

### English

- Added versioned contract migration, content-addressed evidence bundles, slice/distribution gates, evaluator calibration, trace-graph evaluation, dataset leakage controls, CI renderers, portable vendor adapters, and audited blind review.
- Packaged the optional FastAPI workbench with CSP-safe DOM rendering and added Python 3.11-3.13 CI.
- Upgraded the synthetic flagship demo to generate canonical JSON, Markdown, HTML, JUnit, SARIF, GitHub Summary, and verified evidence for executive, engineer, and auditor profiles.
- Added a deterministic ChatGPT skills-only plugin bundle and v2 release evidence.

### Tiếng Việt

- Bổ sung contract có version, evidence bundle content-addressed, slice/distribution gate, calibration, trace graph, chống dataset leakage, CI renderer, vendor adapter và blind review có audit.
- Đóng gói FastAPI workbench tùy chọn với CSP/DOM an toàn và CI Python 3.11-3.13.
- Nâng demo synthetic để xuất cùng một quyết định qua JSON, Markdown, HTML, JUnit, SARIF, GitHub Summary và evidence đã xác minh.

### 日本語

- versioned contract、content-addressed evidence、slice/distribution gate、calibration、trace graph、dataset leakage check、CI renderer、vendor adapter、blind review audit を追加しました。
- CSP-safe な任意 FastAPI workbench と Python 3.11-3.13 CI を同梱しました。
- synthetic flagship demo は同一判定を JSON、Markdown、HTML、JUnit、SARIF、GitHub Summary、検証済み evidence に出力します。

## [1.2.0] - 2026-08-02

### English

- Added skills-only plugin packages and directory metadata for ChatGPT, Codex, Claude Code, Cowork and Kimi Code.
- Added the credential-free customer-support release-gate demonstration and its recorded evidence.
- Restored a release-only GitHub Actions workflow for PyPI Trusted Publishing; runtime integrations remain local CLI/API workflows.

### Tiếng Việt

- Bổ sung package plugin dạng skills-only và metadata directory cho ChatGPT, Codex, Claude Code, Cowork và Kimi Code.
- Bổ sung demo release gate cho customer support không cần credential cùng bằng chứng đã ghi lại.
- Khôi phục GitHub Actions chỉ dùng để phát hành PyPI qua Trusted Publishing; tích hợp runtime vẫn chạy qua CLI/API cục bộ.

### 日本語

- ChatGPT、Codex、Claude Code、Cowork、Kimi Code 向けの skills-only plugin package と directory metadata を追加しました。
- 認証情報不要の customer-support release-gate demo と記録済み証拠を追加しました。
- PyPI Trusted Publishing 専用の GitHub Actions workflow を復元しました。runtime integration は引き続きローカル CLI/API を使用します。

## [1.0.0] - 2026-07-26

### English

- Consolidated deterministic and statistical evaluation, policy comparison, provenance diagnosis, offline evidence and API/CLI adapters into one stable baseline.
- Removed all repository-owned GitHub Actions; release gates remain available through the local CLI and API.
- Standardized the public tag and package version at `v1.0.0`.

### Tiếng Việt

- Hợp nhất đánh giá xác định/thống kê, so sánh policy, chẩn đoán provenance, bằng chứng offline và adapter API/CLI vào một baseline ổn định.
- Xóa toàn bộ GitHub Actions thuộc repo; release gate tiếp tục hoạt động qua CLI và API cục bộ.
- Chuẩn hóa tag public và package version thành `v1.0.0`.

### 日本語

- 決定的・統計的評価、ポリシー比較、来歴診断、オフライン証拠、API/CLI アダプターを1つの安定版へ統合しました。
- リポジトリ所有の GitHub Actions をすべて削除し、リリースゲートはローカル CLI と API で引き続き利用できます。
- 公開タグとパッケージ版を `v1.0.0` に統一しました。

[2.0.1]: https://github.com/thangldw/ragops/releases/tag/v2.0.1
[2.0.0]: https://github.com/thangldw/ragops/releases/tag/v2.0.0
[1.2.0]: https://github.com/thangldw/ragops/releases/tag/v1.2.0
[1.0.0]: https://github.com/thangldw/ragops/releases/tag/v1.0.0
