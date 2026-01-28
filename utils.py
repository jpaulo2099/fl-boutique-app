import uuid
from datetime import datetime, timedelta

def converter_input_para_float(valor_str):
    try:
        if not valor_str: return 0.0
        limpo = str(valor_str).replace("R$", "").replace(" ", "")
        if "." in limpo and "," in limpo:
            limpo = limpo.replace(".", "").replace(",", ".")
        elif "," in limpo:
            limpo = limpo.replace(",", ".")
        return float(limpo)
    except:
        return 0.0

def format_brl(value):
    try:
        if value is None or str(value).strip() == "": return "R$ 0,00"
        val_float = float(value)
        return f"R$ {val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(value)

def format_data_br(data_iso):
    """Converte AAAA-MM-DD para DD/MM/AAAA."""
    try:
        if not data_iso or str(data_iso) == "": return "-"
        data_part = str(data_iso)[:10]
        data_obj = datetime.strptime(data_part, "%Y-%m-%d")
        return data_obj.strftime("%d/%m/%Y")
    except:
        return data_iso

# ATUALIZADO PARA ACEITAR TIPO (VENDA OU DESPESA)
def gerar_lancamentos(total, parcelas, forma, entidade, origem_texto, data_base=None, datas_customizadas=None, tipo="Venda"):
    lancs = []
    hoje = data_base if data_base else datetime.now()
    val_parc = round(total/parcelas, 2)
    dif = round(total - (val_parc * parcelas), 2)
    
    # Se for Despesa à vista (Dinheiro/Pix), status é Pago. Se for parcelado ou cartão, depende.
    # Regra simples: Se parcelas = 1 e (Pix ou Dinheiro), Pago. Senão Pendente.
    status_padrao = "Pago" if (forma in ["Dinheiro", "Pix"] and parcelas == 1) else "Pendente"
    
    for i in range(parcelas):
        if datas_customizadas and len(datas_customizadas) > i:
            venc = datas_customizadas[i]
        else:
            if parcelas == 1: venc = hoje
            else: venc = hoje + timedelta(days=30*(i+1))
            
        val = val_parc + dif if i == parcelas-1 else val_parc
        val_str = f"{val:.2f}"
        
        # Descrição muda se for Venda (Cliente) ou Compra (Fornecedor)
        desc = f"{origem_texto} - {entidade} ({i+1}/{parcelas})"
        
        lancs.append([
            str(uuid.uuid4()),
            hoje.strftime("%Y-%m-%d"),
            venc.strftime("%Y-%m-%d"),
            tipo, # Venda ou Despesa
            desc,
            val_str,
            forma,
            status_padrao
        ])
    return lancs