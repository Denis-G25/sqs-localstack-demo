# Demo Amazon SQS pe LocalStack

Prototip realizat pentru referatul **„Arhitecturi Cloud cu Amazon Web Services. Privire de ansamblu și Validare Practică prin LocalStack”**.

Serviciul ales este **Amazon SQS** (Simple Queue Service), o coadă de mesaje. Exemplul simulează pozițiile GPS ale unei flote auto: un producător trimite poziții în coadă, iar un consumator le citește, le procesează și le șterge. Totul rulează local, pe laptop, prin **LocalStack** (un emulator AWS într-un container Docker), fără cont AWS și fără costuri.

## Ce demonstrează

| Operație | Comandă |
|---|---|
| Creare coadă | `python sqs_demo.py create` |
| Inserare mesaj | `python sqs_demo.py send --plate BH-01-FLT --lat 47.05 --lng 21.92` |
| Inserare 3 mesaje de exemplu | `python sqs_demo.py send-sample` |
| Numărare mesaje | `python sqs_demo.py count` |
| Citire fără ștergere | `python sqs_demo.py peek` |
| Consumare (citire + procesare + ștergere) | `python sqs_demo.py consume` |
| Golire coadă | `python sqs_demo.py purge` |
| Ștergere coadă | `python sqs_demo.py delete-queue` |

## Cerințe

- **Docker Desktop** (cu Docker Compose v2), pornit
- **Python 3.9+** (pe Windows comanda poate fi `py` în loc de `python`)
- Un **cont LocalStack gratuit** (planul Hobby, uz necomercial) pe [app.localstack.cloud](https://app.localstack.cloud). Din 2026, emulatorul pornește doar cu un auth token.

Verificare:

```
docker --version
docker compose version
python --version
```

## 1. Instalare

Clonați repository-ul și intrați în folder:

```
git clone https://github.com/UTILIZATOR/sqs-localstack-demo.git
cd sqs-localstack-demo
```

Creați un mediu virtual și instalați dependența (`boto3`, SDK-ul AWS pentru Python).

Windows (cmd):

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS / Linux:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Configurare (token LocalStack)

1. Intrați pe [app.localstack.cloud](https://app.localstack.cloud), creați contul și copiați token-ul din pagina **Auth Tokens** (începe cu `ls-`).
2. Creați fișierul `.env.localstack` din model și puneți token-ul în el.

Windows (cmd):

```
copy .env.localstack.example .env.localstack
notepad .env.localstack
```

macOS / Linux:

```
cp .env.localstack.example .env.localstack
open -e .env.localstack
```

Fișierul trebuie să conțină o singură linie: `LOCALSTACK_AUTH_TOKEN=ls-...`. Fișierul este în `.gitignore`, deci token-ul nu ajunge pe GitHub.

## 3. Pornirea LocalStack

```
docker compose up -d
docker compose ps
curl http://localhost:4566/_localstack/health
```

La ultima comandă, serviciul `sqs` trebuie să apară cu starea `available` sau `running`. Dacă LocalStack se oprește imediat, vedeți motivul cu `docker compose logs localstack` (cel mai des: token lipsă sau greșit).

## 4. Utilizare

Toate comenzile se rulează din folderul proiectului, cu mediul virtual activat.

```
python sqs_demo.py create
python sqs_demo.py send-sample
python sqs_demo.py count
python sqs_demo.py peek
python sqs_demo.py send --plate BH-01-FLT --lat 47.05 --lng 21.92
python sqs_demo.py consume
python sqs_demo.py count
```

Rezultat așteptat (adresa și valorile pot diferi):

```
Coada creata: http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/gps-positions
Trimis {'plate': 'BH-01-FLT', 'lat': 47.05, 'lng': 21.92}
Trimis {'plate': 'CJ-07-ABC', 'lat': 46.77, 'lng': 23.59}
Trimis {'plate': 'B-123-FLT', 'lat': 44.43, 'lng': 26.1}
Mesaje in coada:        3
Mesaje in procesare:    0
...
Procesez: masina BH-01-FLT la (47.05, 21.92)
Gata: 4 mesaje consumate si sterse.
```

Câteva observații:

- `peek` citește mesajele cu `VisibilityTimeout=0`, deci nu le ascunde și rămân în coadă.
- `consume` șterge fiecare mesaj după procesare, folosind *receipt handle* (nu `MessageId`).
- Un mesaj citit și neșters redevine vizibil după *visibility timeout* (30 s implicit), ca să poată fi reprocesat.

### Aceleași operații cu AWS CLI (opțional)

Dacă aveți AWS CLI v2, aceleași operații se pot face direct din terminal, îndreptând comenzile spre LocalStack.

Windows (cmd):

```
set AWS_ENDPOINT_URL=http://localhost.localstack.cloud:4566
set AWS_ACCESS_KEY_ID=test
set AWS_SECRET_ACCESS_KEY=test
set AWS_DEFAULT_REGION=us-east-1
```

macOS / Linux:

```
export AWS_ENDPOINT_URL=http://localhost.localstack.cloud:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
```

Apoi:

```
aws sqs list-queues
aws sqs get-queue-attributes --queue-url http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/gps-positions --attribute-names ApproximateNumberOfMessages
```

Atenție: o comandă `aws` fără aceste variabile merge la AWS-ul real. `aws sts get-caller-identity` trebuie să arate contul `000000000000`.

## 5. Oprire și curățenie

```
python sqs_demo.py delete-queue
docker compose down
```

LocalStack ține starea în memorie (planul gratuit): la oprire, tot ce ați creat dispare.

## Probleme frecvente

| Simptom | Cauză și rezolvare |
|---|---|
| `Nu ma pot conecta la LocalStack` | LocalStack nu rulează. Verificați cu `docker compose ps` și porniți-l cu `docker compose up -d`. |
| LocalStack se oprește imediat | Token lipsă sau greșit în `.env.localstack`. Vedeți `docker compose logs localstack`. |
| `port is already allocated` pe 4566 | Un alt LocalStack rulează deja (de exemplu pornit cu `lstk`). Opriți-l și verificați cu `docker ps`. |
| `Docker is not available` / eroare la `docker compose` | Docker Desktop nu e pornit. Porniți-l și așteptați „Engine running”. |
| `Coada 'gps-positions' nu exista` | Rulați întâi `python sqs_demo.py create`. După fiecare repornire LocalStack pornește gol. |
| Eroare de rezolvare DNS pentru `localhost.localstack.cloud` | Nu aveți internet sau DNS-ul blochează domeniul. Setați `LOCALSTACK_ENDPOINT=http://localhost:4566` înainte de rulare. |

## Structura proiectului

```
sqs-localstack-demo/
├── compose.yaml                 # pornește LocalStack
├── .env.localstack.example      # model pentru token (copiat în .env.localstack)
├── .gitignore
├── requirements.txt             # boto3
├── sqs_demo.py                  # operațiile SQS
└── README.md
```

## Bibliografie

- LocalStack, documentație oficială: <https://docs.localstack.cloud>
- Amazon SQS, Developer Guide: <https://docs.aws.amazon.com/AWSSimpleQueueService>
- Boto3, SQS client: <https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html>
- Suport de curs CAPI, Curs 3: LocalStack
