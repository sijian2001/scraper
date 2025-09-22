GitHub issueを分析修正する: $ARGUMENTS.

下記のステップで実施してください：

1. GitHub issueの状態を「着手中」に変更
2. GitHub issueの開始日時を設定 (時間まで記載すること)
3. Git で develop からブランチを作成 (ブランチ名は`feature/<GitHub issue ID>`とする)
4. 空コミットを作成 (コミットメッセージは`chore: start feature/<GitHub issue ID>`とする)
5. PR を作成 (`gh pr create --assignee @me --base develop --draft`)
  - GitHub issueのタイトルを参照する (`【<GitHub issue ID>】<タイトル>`)
  - ボディはGitHub issueの内容から生成する
6. 実装計画を考えて、ユーザーに伝える
7. ユーザーにプロンプトを返す

Remember to use the GitHub CLI (`gh`) for all GitHub-related tasks.