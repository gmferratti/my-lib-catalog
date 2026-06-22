- Refatoração do código seguindo boas práticas de clean code e clean architecture once is done
- No caso de prateleira, mudar o ícone. Dar opção de prateleira e nicho
- Ferramenta de crop para as capas para não sair fundo branco no dark mode.
- Botões no modo claro ainda não estão 100%
- Edições de livros de série não são triviais e ficam adicionando travessões desnecessários.
- Clicar na imagem do livro para abrir a edição, não só o título.
- Ainda ficam aparecendo alterações pendentes mesmo após fechar a PR.

Ao separar por vírgula autores
ValueError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
Traceback:

File "/mount/src/my-lib-catalog/ui/app.py", line 37, in <module>
    pg.run()
File "/home/adminuser/venv/lib/python3.12/site-packages/streamlit/navigation/page.py", line 490, in run
    exec(code, module.__dict__)  # noqa: S102
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/mount/src/my-lib-catalog/ui/pages/ficha.py", line 119, in <module>
    paginas_total = int(registro.get("paginas") or 0)
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^