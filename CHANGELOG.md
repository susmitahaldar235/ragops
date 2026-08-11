# RAGOps changelog / Lịch sử thay đổi / 変更履歴

## Unreleased

### English

- Added an offline Phoenix recorded-score adapter example that preserves producer-owned score meaning, scale, and direction while enforcing complete case coverage.

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

[1.2.0]: https://github.com/thangldw/ragops/releases/tag/v1.2.0
[1.0.0]: https://github.com/thangldw/ragops/releases/tag/v1.0.0
