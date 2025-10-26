
## Estrutura do projeto

### Pré-requisitos

* instalar o wsl2. https://marcelo-albuquerque.medium.com/como-instalar-o-wsl-2-no-windows-10-3e26d99d7161

* Instalar o Docker (preferencialmente a partir da linha de comando). https://medium.com/@yoursemicolon/docker-installation-from-windows-powershell-ef1d31b0844b



### Clone (baixar) o projeto com todos os arquivos fornecidos do repositorio no Github:

Comandos :


``` bash
# baixar os arquivos
 git clone https://github.com/carlosducruz/gestaocontrato.git

 # entrar na pasta do projeto
 cd .\gestaocontrato\

 # entrar no ramo de trabalho versao_1
 git checkout feature/versao_1

 # obter as ultimas alterações
 git pull

# verificar se todos os arquivos foram atualizados
 git status

```


A estrutura de pastas:

``` bash
.
├── app.py                 # Aplicação Flask principal
├── requirements.txt       # Dependências Python
├── Dockerfile             # Configuração da imagem Docker
├── docker-compose.yml     # Orquestração dos containers
├── README.md              # Este arquivo
└── templates/             # Templates HTML
    ├── base.html
    ├── login.html
    ├── register.html
    ├── home.html
    ├── profile.html
    └── ... e demais páginas
```

## Executar a aplicação    

### no modo de teste no docker (Executar no container)
``` bash


docker-compose up --build
#ou
docker compose up --build
```

## no modo de desenvolvimento  (Executar direto na maquina [opcional])

### configurar ambiente local
 
#### no terminal:

``` bash
#verificar se esta instalado
python --version
pip --version

#instalar pipenv caso não tenha a pasta venv
pipenv install
 
#instalar as libs auxiliares 
pipenv install -r requirements.txt
 
```

#### abra um terminal com  e execute para subir o banco de dados

``` bash
 

docker compose up -d db
#ou
docker-compose up -d db

```

#### no vs code :
* Ctrl + Shift + P
Python select interpreter:
Pipenv (Python 3.x) [path_to_virtualenv]

* Vá ao menu executar e de um play em Flask Debug

## Acessar a aplicação 

* URL: http://localhost:5000

* Usuário padrão: admin

* Senha padrão: admin123
