# papnt

from https://github.com/issakuss/papnt

- [Notionでの論文管理をサポートするツールを作りました](https://qiita.com/issakuss/items/2e69f2da040cb35ed0d3)

## コンテナ起動

- `bibfiles` フォルダを作成しておく

- ビルド（初回のみ）

```shell
docker compose build
```

- 実行（シェル起動）

```shell
docker compose run --rm papnt
```

## papnt usage

- データベースに記入されたDOIをもとに，CrossRef の API を使って情報を埋める

```shell
papnt doi
```

- データベースに記入されたDOIをもとに，JaLC の API を使って情報を埋める

```shell
papnt jalc
```

- データベースに記入されたbibをもとに情報を埋める

```shell
papnt bib
```

- データベースにアップロードされたPDFファイルをもとに，情報を埋める

```shell
papnt pdf
```

- ローカルにある論文PDFファイルのパスを指定し，その論文の情報を埋める

```shell
papnt paths <論文PDFファイルのパス>
```

```shell
papnt paths <論文PDFファイルのパス>,<論文PDFファイルのパス>
```

```shell
papnt paths <論文PDFファイルのあるディレクトリへのパス>
```

- `Cite-in` プロパティについた特定のタグの論文から `bibfiles` に bib ファイルを作成する

```shell
papnt makebib <タグ>
```
