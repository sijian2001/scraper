GitHub issue を分析修正する: $ARGUMENTS.

下記のステップで実施してください：

1. PR のステータスを ready にする
2. PR をマージ (`gh pr merge --merge --auto --delete-branch`)
3. GitHub issue の開始日時を設定 (時間まで記載すること)
4. GitHub issue に「サマリー」を追加
  - コマンドライン履歴とコンテキストを参照して、振り返りを効率かするための文章を作成
5. GitHub issue の状態を「完了」に変更
6. GitHub issue の完了日時を記載 (時間まで記載すること)
7. ユーザーにプロンプトを返す

Remember to use the GitHub CLI (`gh`) for all GitHub-related tasks.