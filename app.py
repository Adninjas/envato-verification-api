from flask import Flask, jsonify, request
import imaplib
import email
from email.header import decode_header
import re
import logging
import os
from urllib.parse import unquote

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

# Configurações IMAP para o webmail da Hostinger
IMAP_SERVER = "imap.hostinger.com"
IMAP_USER = os.getenv('IMAP_USER', 'suporte@adninjas.pro')  # Ajuste para o e-mail que recebe os códigos da Envato
IMAP_PASSWORD = os.getenv('IMAP_PASSWORD', 'Keylogger#0!')  # Ajuste para a senha do e-mail

def fetch_verification_code():
    try:
        # Conectar ao servidor IMAP
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, timeout=30)
        logging.info("Conexão IMAP estabelecida com imap.hostinger.com")
        
        # Fazer login
        mail.login(IMAP_USER, IMAP_PASSWORD)
        logging.info("Login IMAP bem-sucedido")

        # Selecionar a pasta 'INBOX'
        status, data = mail.select('INBOX')
        if status != 'OK':
            raise Exception(f"Erro ao selecionar 'INBOX': {data}")
        logging.info("Pasta 'INBOX' selecionada com sucesso")

        # Busca por e-mails da Envato (usando o remetente ou assunto)
        search_criteria = '(FROM "envato")'  # Busca por e-mails do remetente Envato
        status, email_ids = mail.search(None, search_criteria)
        if status != 'OK':
            raise Exception(f"Erro na busca IMAP: {email_ids}")
        email_ids = email_ids[0].split()
        if not email_ids:
            raise Exception("Nenhum e-mail encontrado com o critério 'FROM envato'")

        # Pegar o e-mail mais recente
        latest_email_id = email_ids[-1]
        status, msg_data = mail.fetch(latest_email_id, '(RFC822)')
        if status != 'OK':
            raise Exception(f"Erro ao buscar e-mail: {msg_data}")

        msg = email.message_from_bytes(msg_data[0][1])
        subject = decode_header(msg['subject'])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()
        logging.info(f"Assunto do e-mail: {subject}")

        # Extrair o código de verificação do corpo do e-mail
        code = None

        for part in msg.walk():
            if part.get_content_type() == 'text/plain':  # Verificar texto simples
                body = part.get_payload(decode=True).decode()
                logging.info(f"Corpo do e-mail em texto simples: {body}")

                # Regex para capturar 10 dígitos (código de verificação da Envato)
                code = re.search(r"(\d{10})", body)
                if code:
                    logging.info(f"Código de verificação encontrado: {code.group(1)}")
                    break

            elif part.get_content_type() == 'text/html':  # Verificar e-mail em HTML
                body = part.get_payload(decode=True).decode()
                logging.info(f"Corpo do e-mail em HTML: {body}")
                code = re.search(r"(\d{10})", body)
                if code:
                    logging.info(f"Código de verificação encontrado: {code.group(1)}")
                    break

        # Verifica se o código foi encontrado
        if code:
            return code.group(1)
        else:
            raise Exception("Nenhum código de verificação encontrado no e-mail")

    except Exception as e:
        logging.error(f"Erro: {str(e)}")
        raise
    finally:
        try:
            mail.logout()
            logging.info("Logout IMAP realizado")
        except:
            pass

@app.route('/get-verification-code', methods=['GET'])
def get_verification_code():
    try:
        phone = request.args.get('phone')
        phone = unquote(phone)  # Decodificar a URL codificada

        logging.info(f"Telefone recebido após decodificação: {phone}")

        if not phone:
            raise Exception("Número de telefone não fornecido na requisição")

        # Remover espaços ou caracteres não visíveis do número de telefone
        phone = phone.strip()

        # Verificar se o número começa com "+" e tem exatamente 14 caracteres (considerando o "+55")
        if not phone.startswith('+'):
            phone = '+' + phone
        
        if len(phone) != 14:
            raise Exception("Número de telefone inválido. Formato esperado: +55XXXXXXXXXXX")
        
        logging.info(f"Telefone validado: {phone}")

        # Chama a função para obter o código
        code = fetch_verification_code()

        return jsonify({"status": "success", "code": code}), 200
    except Exception as e:
        logging.error(f"Erro: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port, host="0.0.0.0")