import re

def redact_pii(text: str) -> str:
    """
    Remove PII (CPF, email, telefone, instalação) de textos ENEL.
    """
    if not text:
        return text
        
    # CPF: 000.000.000-00 ou 00000000000
    text = re.sub(r'\d{3}\.\d{3}\.\d{3}-\d{2}', '[CPF_REDACTED]', text)
    text = re.sub(r'\b\d{11}\b', '[CPF_REDACTED]', text)
    
    # Email
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
    
    # Telefone: (00) 00000-0000 ou variações
    text = re.sub(r'\(?\d{2}\)?\s?\d{4,5}-?\d{4}', '[PHONE_REDACTED]', text)
    
    # Instalação (ENEL costuma ter ~10 dígitos)
    # text = re.sub(r'\b\d{10}\b', '[INSTALLATION_REDACTED]', text)
    
    return text
