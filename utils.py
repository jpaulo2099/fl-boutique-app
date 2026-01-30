import database as db
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

def gerar_lancamentos(total, parcelas, forma, cli, origem_texto, data_base, datas_customizadas=None, tipo="Receita"):
    """
    Gera uma lista de lançamentos financeiros (parcelas).
    Lógica de Status Inteligente:
    - Dinheiro/Débito: Sempre 'Pago'.
    - Pix: 'Pago' se for hoje, 'Pendente' se for futuro.
    - Cartão/Boleto: Sempre 'Pendente'.
    """
    lancs = []  # <--- Mantido como 'lancs' conforme seu padrão
    
    # Garante que total é float
    if isinstance(total, str):
        total = converter_input_para_float(total)
        
    valor_parcela = total / parcelas
    
    # Data de hoje para comparação (apenas a data, sem horas)
    hoje = datetime.now().date()
    
    for i in range(parcelas):
        # 1. Definir Data de Vencimento
        if datas_customizadas and i < len(datas_customizadas):
            # Se vier do Date Input do Streamlit, já é objeto date
            data_venc = datas_customizadas[i]
        else:
            # Cálculo simples: 30 dias a mais por parcela
            # Garante que data_base seja convertida corretamente
            if isinstance(data_base, str):
                d_base = datetime.strptime(data_base, "%Y-%m-%d").date()
            elif isinstance(data_base, datetime):
                d_base = data_base.date()
            else:
                d_base = data_base
                
            data_venc = d_base + timedelta(days=30 * i)
            
        # 2. Definir Status Inteligente
        status = "Pendente" # Começa como pendente por segurança
        
        if forma == "Pix":
            # Se a data de vencimento for hoje ou já passou, considera Pago.
            # Se for futura (ex: Pix agendado para mês que vem), entra como Pendente.
            if data_venc <= hoje:
                status = "Pago"
            else:
                status = "Pendente"
        
        elif forma in ["Dinheiro", "Débito"]:
            # Dinheiro e Débito presencial são sempre liquidez imediata
            status = "Pago"
            
        # Cartão de Crédito (30 dias pra cair) e Boleto ficam Pendentes
        else:
            status = "Pendente"
            
        # 3. Criar registro
        # [id, data_lanc, data_venc, tipo, descricao, valor, forma, status]
        lancs.append([
            str(uuid.uuid4()),
            datetime.now().strftime("%Y-%m-%d"), # Data Lançamento (Hoje)
            data_venc.strftime("%Y-%m-%d"),      # Data Vencimento
            tipo,
            f"{origem_texto} - {cli} ({i+1}/{parcelas})",
            f"{valor_parcela:.2f}",
            forma,
            status
        ])
        
    return lancs

def calcular_preco_sugerido(custo_produto):
    """
    Calcula o preço de venda sugerido baseando-se nas configs do banco.
    Fórmula: (Custo + Custo_Fixo) * Markup * Taxa_Extra
    """
    try:
        if custo_produto <= 0: return 0.0
        
        # Pega do banco (ou usa padrão se falhar)
        conf = db.get_configs()
        c_fixo = conf.get('custo_fixo', 1.06)
        markup = conf.get('markup', 2.0)
        t_extra = conf.get('taxa_extra', 1.12)
        
        sugestao = (custo_produto + c_fixo) * markup * t_extra
        return round(sugestao, 2)
    except:
        return 0.0