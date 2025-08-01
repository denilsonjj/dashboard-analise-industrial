import pandas as pd
import re

# DAX completo como string
dax_data ="""
    {
        -- JANEIRO
        { "2025-01-01", "Improdutivo" }, { "2025-01-02", "Produtivo" }, { "2025-01-03", "Produtivo" }, { "2025-01-04", "Improdutivo" }, { "2025-01-05", "Improdutivo" },
        { "2025-01-06", "Produtivo" }, { "2025-01-07", "Produtivo" }, { "2025-01-08", "Produtivo" }, { "2025-01-09", "Produtivo" }, { "2025-01-10", "Produtivo" },
        { "2025-01-11", "Produtivo" }, { "2025-01-12", "Improdutivo" }, { "2025-01-13", "Produtivo" }, { "2025-01-14", "Produtivo" }, { "2025-01-15", "Produtivo" },
        { "2025-01-16", "Produtivo" }, { "2025-01-17", "Produtivo" }, { "2025-01-18", "Produtivo" }, { "2025-01-19", "Improdutivo" }, { "2025-01-20", "Produtivo" },
        { "2025-01-21", "Produtivo" }, { "2025-01-22", "Produtivo" }, { "2025-01-23", "Produtivo" }, { "2025-01-24", "Produtivo" }, { "2025-01-25", "Improdutivo" },
        { "2025-01-26", "Improdutivo" }, { "2025-01-27", "Produtivo" }, { "2025-01-28", "Produtivo" }, { "2025-01-29", "Produtivo" }, { "2025-01-30", "Produtivo" }, { "2025-01-31", "Produtivo" },

        -- FEVEREIRO
        { "2025-02-01", "Improdutivo" }, { "2025-02-02", "Improdutivo" }, { "2025-02-03", "Produtivo" }, { "2025-02-04", "Produtivo" }, { "2025-02-05", "Produtivo" },
        { "2025-02-06", "Produtivo" }, { "2025-02-07", "Produtivo" }, { "2025-02-08", "Improdutivo" }, { "2025-02-09", "Improdutivo" }, { "2025-02-10", "Produtivo" },
        { "2025-02-11", "Produtivo" }, { "2025-02-12", "Produtivo" }, { "2025-02-13", "Produtivo" }, { "2025-02-14", "Produtivo" }, { "2025-02-15", "Improdutivo" },
        { "2025-02-16", "Improdutivo" }, { "2025-02-17", "Produtivo" }, { "2025-02-18", "Produtivo" }, { "2025-02-19", "Produtivo" }, { "2025-02-20", "Produtivo" },
        { "2025-02-21", "Produtivo" }, { "2025-02-22", "Improdutivo" }, { "2025-02-23", "Improdutivo" }, { "2025-02-24", "Produtivo" }, { "2025-02-25", "Produtivo" },
        { "2025-02-26", "Produtivo" }, { "2025-02-27", "Produtivo" }, { "2025-02-28", "Produtivo" },

        -- MARÇO
        { "2025-03-01", "Improdutivo" }, { "2025-03-02", "Improdutivo" }, { "2025-03-03", "Improdutivo" }, { "2025-03-04", "Improdutivo" }, { "2025-03-05", "Improdutivo" },
        { "2025-03-06", "Improdutivo" }, { "2025-03-07", "Improdutivo" }, { "2025-03-08", "Improdutivo" }, { "2025-03-09", "Improdutivo" }, { "2025-03-10", "Produtivo" },
        { "2025-03-11", "Produtivo" }, { "2025-03-12", "Produtivo" }, { "2025-03-13", "Produtivo" }, { "2025-03-14", "Produtivo" }, { "2025-03-15", "Improdutivo" },
        { "2025-03-16", "Improdutivo" }, { "2025-03-17", "Produtivo" }, { "2025-03-18", "Produtivo" }, { "2025-03-19", "Produtivo" }, { "2025-03-20", "Produtivo" },
        { "2025-03-21", "Produtivo" }, { "2025-03-22", "Improdutivo" }, { "2025-03-23", "Improdutivo" }, { "2025-03-24", "Produtivo" }, { "2025-03-25", "Produtivo" },
        { "2025-03-26", "Produtivo" }, { "2025-03-27", "Produtivo" }, { "2025-03-28", "Produtivo" }, { "2025-03-29", "Produtivo" }, { "2025-03-30", "Improdutivo" }, { "2025-03-31", "Produtivo" },

        -- ABRIL
        { "2025-04-01", "Produtivo" }, { "2025-04-02", "Produtivo" }, { "2025-04-03", "Produtivo" }, { "2025-04-04", "Produtivo" }, { "2025-04-05", "Improdutivo" },
        { "2025-04-06", "Improdutivo" }, { "2025-04-07", "Produtivo" }, { "2025-04-08", "Produtivo" }, { "2025-04-09", "Produtivo" }, { "2025-04-10", "Produtivo" },
        { "2025-04-11", "Produtivo" }, { "2025-04-12", "Produtivo" }, { "2025-04-13", "Improdutivo" }, { "2025-04-14", "Produtivo" }, { "2025-04-15", "Produtivo" },
        { "2025-04-16", "Produtivo" }, { "2025-04-17", "Produtivo" }, { "2025-04-18", "Improdutivo" }, { "2025-04-19", "Improdutivo" }, { "2025-04-20", "Improdutivo" },
        { "2025-04-21", "Improdutivo" }, { "2025-04-22", "Produtivo" }, { "2025-04-23", "Produtivo" }, { "2025-04-24", "Produtivo" }, { "2025-04-25", "Produtivo" },
        { "2025-04-26", "Improdutivo" }, { "2025-04-27", "Improdutivo" }, { "2025-04-28", "Produtivo" }, { "2025-04-29", "Produtivo" }, { "2025-04-30", "Produtivo" },

        -- MAIO
        { "2025-05-01", "Improdutivo" }, { "2025-05-02", "Produtivo" }, { "2025-05-03", "Improdutivo" }, { "2025-05-04", "Improdutivo" }, { "2025-05-05", "Produtivo" },
        { "2025-05-06", "Produtivo" }, { "2025-05-07", "Produtivo" }, { "2025-05-08", "Produtivo" }, { "2025-05-09", "Produtivo" }, { "2025-05-10", "Improdutivo" },
        { "2025-05-11", "Improdutivo" }, { "2025-05-12", "Produtivo" }, { "2025-05-13", "Produtivo" }, { "2025-05-14", "Produtivo" }, { "2025-05-15", "Produtivo" },
        { "2025-05-16", "Produtivo" }, { "2025-05-17", "Improdutivo" }, { "2025-05-18", "Improdutivo" }, { "2025-05-19", "Produtivo" }, { "2025-05-20", "Produtivo" },
        { "2025-05-21", "Produtivo" }, { "2025-05-22", "Produtivo" }, { "2025-05-23", "Produtivo" }, { "2025-05-24", "Improdutivo" }, { "2025-05-25", "Improdutivo" },
        { "2025-05-26", "Produtivo" }, { "2025-05-27", "Produtivo" }, { "2025-05-28", "Produtivo" }, { "2025-05-29", "Produtivo" }, { "2025-05-30", "Produtivo" },
        { "2025-05-31", "Produtivo" },

        -- JUNHO
        { "2025-06-01", "Improdutivo" }, { "2025-06-02", "Produtivo" }, { "2025-06-03", "Produtivo" }, { "2025-06-04", "Produtivo" }, { "2025-06-05", "Produtivo" },
        { "2025-06-06", "Produtivo" }, { "2025-06-07", "Improdutivo" }, { "2025-06-08", "Improdutivo" }, { "2025-06-09", "Produtivo" }, { "2025-06-10", "Produtivo" },
        { "2025-06-11", "Produtivo" }, { "2025-06-12", "Produtivo" }, { "2025-06-13", "Produtivo" }, { "2025-06-14", "Produtivo" }, { "2025-06-15", "Improdutivo" },
        { "2025-06-16", "Produtivo" }, { "2025-06-17", "Produtivo" }, { "2025-06-18", "Produtivo" }, { "2025-06-19", "Produtivo" }, { "2025-06-20", "Produtivo" },
        { "2025-06-21", "Improdutivo" }, { "2025-06-22", "Improdutivo" }, { "2025-06-23", "Produtivo" }, { "2025-06-24", "Produtivo" }, { "2025-06-25", "Produtivo" },
        { "2025-06-26", "Produtivo" }, { "2025-06-27", "Produtivo" }, { "2025-06-28", "Improdutivo" }, { "2025-06-29", "Improdutivo" }, { "2025-06-30", "Produtivo" },
        
        -- JULHO
        { "2025-07-01", "Produtivo" }, { "2025-07-02", "Produtivo" }, { "2025-07-03", "Produtivo" }, { "2025-07-04", "Produtivo" }, { "2025-07-05", "Improdutivo" },
        { "2025-07-06", "Improdutivo" }, { "2025-07-07", "Produtivo" }, { "2025-07-08", "Produtivo" }, { "2025-07-09", "Improdutivo" }, { "2025-07-10", "Produtivo" },
        { "2025-07-11", "Produtivo" }, { "2025-07-12", "Improdutivo" }, { "2025-07-13", "Improdutivo" }, { "2025-07-14", "Produtivo" }, { "2025-07-15", "Produtivo" },
        { "2025-07-16", "Produtivo" }, { "2025-07-17", "Produtivo" }, { "2025-07-18", "Produtivo" }, { "2025-07-19", "Improdutivo" }, { "2025-07-20", "Improdutivo" },
        { "2025-07-21", "Produtivo" }, { "2025-07-22", "Produtivo" }, { "2025-07-23", "Produtivo" }, { "2025-07-24", "Produtivo" }, { "2025-07-25", "Produtivo" },
        { "2025-07-26", "Improdutivo" }, { "2025-07-27", "Improdutivo" }, { "2025-07-28", "Produtivo" }, { "2025-07-29", "Produtivo" }, { "2025-07-30", "Produtivo" }, { "2025-07-31", "Produtivo" },

        -- AGOSTO
        { "2025-08-01", "Produtivo" }, { "2025-08-02", "Improdutivo" }, { "2025-08-03", "Improdutivo" }, { "2025-08-04", "Produtivo" }, { "2025-08-05", "Produtivo" },
        { "2025-08-06", "Produtivo" }, { "2025-08-07", "Produtivo" }, { "2025-08-08", "Produtivo" }, { "2025-08-09", "Improdutivo" }, { "2025-08-10", "Improdutivo" },
        { "2025-08-11", "Produtivo" }, { "2025-08-12", "Produtivo" }, { "2025-08-13", "Produtivo" }, { "2025-08-14", "Produtivo" }, { "2025-08-15", "Produtivo" },
        { "2025-08-16", "Improdutivo" }, { "2025-08-17", "Improdutivo" }, { "2025-08-18", "Produtivo" }, { "2025-08-19", "Produtivo" }, { "2025-08-20", "Produtivo" },
        { "2025-08-21", "Produtivo" }, { "2025-08-22", "Produtivo" }, { "2025-08-23", "Improdutivo" }, { "2025-08-24", "Improdutivo" }, { "2025-08-25", "Produtivo" },
        { "2025-08-26", "Produtivo" }, { "2025-08-27", "Produtivo" }, { "2025-08-28", "Produtivo" }, { "2025-08-29", "Produtivo" }, { "2025-08-30", "Improdutivo" }, { "2025-08-31", "Improdutivo" },

        -- SETEMBRO
        { "2025-09-01", "Produtivo" }, { "2025-09-02", "Produtivo" }, { "2025-09-03", "Produtivo" }, { "2025-09-04", "Produtivo" }, { "2025-09-05", "Produtivo" },
        { "2025-09-06", "Improdutivo" }, { "2025-09-07", "Improdutivo" }, { "2025-09-08", "Produtivo" }, { "2025-09-09", "Produtivo" }, { "2025-09-10", "Produtivo" },
        { "2025-09-11", "Produtivo" }, { "2025-09-12", "Produtivo" }, { "2025-09-13", "Improdutivo" }, { "2025-09-14", "Improdutivo" }, { "2025-09-15", "Produtivo" },
        { "2025-09-16", "Produtivo" }, { "2025-09-17", "Produtivo" }, { "2025-09-18", "Produtivo" }, { "2025-09-19", "Produtivo" }, { "2025-09-20", "Improdutivo" },
        { "2025-09-21", "Improdutivo" }, { "2025-09-22", "Produtivo" }, { "2025-09-23", "Produtivo" }, { "2025-09-24", "Produtivo" }, { "2025-09-25", "Produtivo" },
        { "2025-09-26", "Produtivo" }, { "2025-09-27", "Improdutivo" }, { "2025-09-28", "Improdutivo" }, { "2025-09-29", "Produtivo" }, { "2025-09-30", "Produtivo" },

        -- OUTUBRO
        { "2025-10-01", "Produtivo" }, { "2025-10-02", "Produtivo" }, { "2025-10-03", "Produtivo" }, { "2025-10-04", "Improdutivo" }, { "2025-10-05", "Improdutivo" },
        { "2025-10-06", "Produtivo" }, { "2025-10-07", "Produtivo" }, { "2025-10-08", "Produtivo" }, { "2025-10-09", "Produtivo" }, { "2025-10-10", "Produtivo" },
        { "2025-10-11", "Improdutivo" }, { "2025-10-12", "Improdutivo" }, { "2025-10-13", "Produtivo" }, { "2025-10-14", "Produtivo" }, { "2025-10-15", "Improdutivo" },
        { "2025-10-16", "Produtivo" }, { "2025-10-17", "Produtivo" }, { "2025-10-18", "Improdutivo" }, { "2025-10-19", "Improdutivo" }, { "2025-10-20", "Produtivo" },
        { "2025-10-21", "Produtivo" }, { "2025-10-22", "Produtivo" }, { "2025-10-23", "Produtivo" }, { "2025-10-24", "Produtivo" }, { "2025-10-25", "Improdutivo" },
        { "2025-10-26", "Improdutivo" }, { "2025-10-27", "Produtivo" }, { "2025-10-28", "Improdutivo" }, { "2025-10-29", "Produtivo" }, { "2025-10-30", "Produtivo" }, { "2025-10-31", "Produtivo" },

        -- NOVEMBRO
        { "2025-11-01", "Improdutivo" }, { "2025-11-02", "Improdutivo" }, { "2025-11-03", "Produtivo" }, { "2025-11-04", "Produtivo" }, { "2025-11-05", "Produtivo" },
        { "2025-11-06", "Produtivo" }, { "2025-11-07", "Produtivo" }, { "2025-11-08", "Improdutivo" }, { "2025-11-09", "Improdutivo" }, { "2025-11-10", "Produtivo" },
        { "2025-11-11", "Produtivo" }, { "2025-11-12", "Produtivo" }, { "2025-11-13", "Produtivo" }, { "2025-11-14", "Produtivo" }, { "2025-11-15", "Improdutivo" },
        { "2025-11-16", "Improdutivo" }, { "2025-11-17", "Produtivo" }, { "2025-11-18", "Produtivo" }, { "2025-11-19", "Improdutivo" }, { "2025-11-20", "Improdutivo" },
        { "2025-11-21", "Improdutivo" }, { "2025-11-22", "Improdutivo" }, { "2025-11-23", "Improdutivo" }, { "2025-11-24", "Produtivo" }, { "2025-11-25", "Produtivo" },
        { "2025-11-26", "Produtivo" }, { "2025-11-27", "Produtivo" }, { "2025-11-28", "Produtivo" }, { "2025-11-29", "Improdutivo" }, { "2025-11-30", "Improdutivo" },
        
        -- DEZEMBRO
        { "2025-12-01", "Produtivo" }, { "2025-12-02", "Produtivo" }, { "2025-12-03", "Produtivo" }, { "2025-12-04", "Produtivo" }, { "2025-12-05", "Produtivo" },
        { "2025-12-06", "Improdutivo" }, { "2025-12-07", "Improdutivo" }, { "2025-12-08", "Improdutivo" }, { "2025-12-09", "Produtivo" }, { "2025-12-10", "Produtivo" },
        { "2025-12-11", "Produtivo" }, { "2025-12-12", "Produtivo" }, { "2025-12-13", "Improdutivo" }, { "2025-12-14", "Improdutivo" }, { "2025-12-15", "Produtivo" },
        { "2025-12-16", "Produtivo" }, { "2025-12-17", "Produtivo" }, { "2025-12-18", "Produtivo" }, { "2025-12-19", "Produtivo" }, { "2025-12-20", "Improdutivo" },
        { "2025-12-21", "Improdutivo" }, { "2025-12-22", "Improdutivo" }, { "2025-12-23", "Improdutivo" }, { "2025-12-24", "Improdutivo" }, { "2025-12-25", "Improdutivo" },
        { "2025-12-26", "Improdutivo" }, { "2025-12-27", "Improdutivo" }, { "2025-12-28", "Improdutivo" }, { "2025-12-29", "Improdutivo" }, { "2025-12-30", "Improdutivo" }, { "2025-12-31", "Improdutivo" }
    }
)
"""

try:
    # Extrai as datas e tipos
    data = re.findall(r'\{ "(\d{4}-\d{2}-\d{2})", "(.*?)" \}', dax_data)

    if not data:
        raise ValueError("Nenhum dado encontrado no formato esperado.")

    df_calendario = pd.DataFrame(data, columns=['Data', 'Tipo'])
    df_calendario['Data'] = pd.to_datetime(df_calendario['Data'])

    print("DataFrame criado com sucesso:")
    print(df_calendario.head())

    # --- LINHA PARA SALVAR O ARQUIVO CSV ---
    nome_arquivo_csv = 'calendario_produtivo.csv'
    df_calendario.to_csv(nome_arquivo_csv, index=False)

    print(f"\nArquivo '{nome_arquivo_csv}' salvo com sucesso!")


except Exception as e:
    print(f"Ocorreu um erro: {e}")