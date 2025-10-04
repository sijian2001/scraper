GitHubのレポジトリを作成する: $ARGUMENTS

下記のステップで実施してください：

1. ソース、README.mdを理解する。
2. 初期化してください。(`/init`)
3. ローカルのソースをgitで管理して、mainブランチをコミットする
4. githubのrepositoryを作成する。(`gh repo create $new-repository --description="$project-description" --source=. --public --push`)
5. auto-merge有効化する。(`gh repo edit sijian2001/$new-repository --delete-branch-on-merge`)
6. mainブランチから、developブランチを作成する。

Remember to use the GitHub CLI (`gh`) for all GitHub-related tasks.