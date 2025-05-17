import telegram
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, CallbackContext
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import requests  # Importe a biblioteca requests para fazer requisições HTTP

# Substitua 'SEU_TOKEN_AQUI' pelo token do seu bot
TOKEN = '7745631278:AAEv-RQLimflS-VgAzQfo2LX-aPiukHwKiE'
GOOGLE_API_KEY = 'AIzaSyDzYPpOvwRoqrfNdn7W-chgbnm8n7aV7rE' # Certifique-se de que esta é a sua chave correta

genai.configure(api_key=GOOGLE_API_KEY)

safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

modelo = genai.GenerativeModel('gemini-2.0-flash', safety_settings=safety_settings)

(OBJETIVO, LOCALIZACAO, INTERESSES, NOVA_PESQUISA) = range(4)

async def start(update: telegram.Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        'Olá! Bem-vindo ao ZéUrna, seu guia para as eleições! 🗳️\n'
        'Para começar, qual o tipo de candidato que você procura (ex: Presidente, Vereador, Deputado Estadual, etc.)?'
    )
    return OBJETIVO

async def receber_tipo(update: telegram.Update, context: CallbackContext) -> int:
    tipo_candidato = update.message.text.strip().lower()
    context.user_data['tipo_candidato'] = tipo_candidato
    if tipo_candidato in ['presidente', 'deputado federal']:
        await update.message.reply_text(f'Entendi! E o que você procura em um candidato? Quais são suas prioridades e causas importantes?')
        return INTERESSES
    elif tipo_candidato in ['governador', 'deputado estadual', 'senador']:
        await update.message.reply_text(f'Certo! Em qual estado você vota?')
        return LOCALIZACAO
    elif tipo_candidato == 'vereador':
        await update.message.reply_text(f'Certo! Em qual cidade você vota?')
        return LOCALIZACAO
    else:
        await update.message.reply_text(
            'Desculpe, não identifiquei o tipo de candidato que você procura. Por favor, informe novamente (ex: Presidente, Vereador, Deputado Estadual, etc.).'
        )
        return OBJETIVO

async def receber_localizacao(update: telegram.Update, context: CallbackContext) -> int:
    localizacao = update.message.text.strip()
    context.user_data['localizacao'] = localizacao

    if await verificar_localizacao(localizacao):
        await update.message.reply_text(
            f'Entendi! E o que você procura em um candidato para {context.user_data["tipo_candidato"]} em {localizacao}? Quais são suas prioridades e causas importantes?'
        )
        return INTERESSES
    else:
        await update.message.reply_text(
            'Desculpe, não consegui encontrar essa localidade no Brasil. Por favor, verifique se digitou corretamente e tente novamente.'
        )
        return LOCALIZACAO

async def verificar_localizacao(localizacao: str) -> bool:
    """Verifica se a localidade existe no Brasil usando a API do IBGE."""
    try:
        url = f"https://servicodados.ibge.gov.br/api/v1/localidades/municipios?nome={localizacao}"
        response = requests.get(url)
        response.raise_for_status()  # Lança uma exceção para erros HTTP 4xx ou 5xx
        data = response.json()
        return len(data) > 0  # Retorna True se a localidade foi encontrada
    except requests.exceptions.RequestException:
        return False  # Retorna False em caso de erro na requisição

async def buscar_candidatos(update: telegram.Update, context: CallbackContext) -> int:
    tipo_candidato = context.user_data.get('tipo_candidato')
    localizacao = context.user_data.get('localizacao', '')  # Localização é opcional para presidente
    interesses = update.message.text.strip()

    if not tipo_candidato or not interesses:
        await update.message.reply_text('Por favor, informe o tipo de candidato e suas prioridades.')
        return INTERESSES

    prompt_usuario = f"""Considerando um eleitor que busca um(a) candidato(a) para o cargo de {tipo_candidato}"""
    if localizacao:
        prompt_usuario += f" na região de {localizacao}"
    prompt_usuario += f""" e que prioriza as seguintes características e propostas: {interesses}. Quais são alguns nomes de possíveis candidatos e seus respectivos números (se disponíveis) para essa eleição? 
    busque nos sites do TRE, materias de jornais e sites de campanha.
    Formate a resposta de forma que fique de fácil leitura em uma conversa do telegram, contendo o Nome do Candidato, o número do Candidato e as propsotas dele que são ligadas ao tema da busca, mas não mencione nada sobre a formatação na resposta.

Por fim, forneça um breve resumo de como as propostas se relacionam com essas causas. Retorne tudo de forma objetiva. caso não ache uma resposta verdadeira, não faça sugestões e também não dê exemplos de como seria uma."""

    await update.message.reply_text('Buscando informações... aguarde um momento.')
    try:
        response = await modelo.generate_content_async(prompt_usuario)
        await update.message.reply_text(response.text)
        await update.message.reply_text(
            'Deseja realizar outra pesquisa?',
            reply_markup=ReplyKeyboardMarkup([['Sim', 'Não']], one_time_keyboard=True, resize_keyboard=True)
        )
        return NOVA_PESQUISA
    except Exception as e:
        print(f"Erro ao gerar conteúdo: {e}")
        await update.message.reply_text(f"Desculpe, não consegui processar sua solicitação no momento devido a um erro: {e}")
        await update.message.reply_text(
            'Deseja tentar novamente?',
            reply_markup=ReplyKeyboardMarkup([['Sim', 'Não']], one_time_keyboard=True, resize_keyboard=True)
        )
        return NOVA_PESQUISA

async def nova_pesquisa(update: telegram.Update, context: CallbackContext) -> int:
    resposta = update.message.text.lower()
    if resposta == 'sim':
        await update.message.reply_text('Ok, vamos iniciar uma nova pesquisa!', reply_markup=ReplyKeyboardRemove())
        return await start(update, context)
    else:
        await update.message.reply_text('Ok, obrigado por usar o ZéUrna! 😊', reply_markup=ReplyKeyboardRemove())
        context.user_data.clear()
        return ConversationHandler.END

async def cancelar(update: telegram.Update, context: CallbackContext) -> int:
    context.user_data.clear()
    await update.message.reply_text('Operação cancelada. Se precisar de ajuda novamente, use /start.')
    return ConversationHandler.END

async def iniciar_conversa(update: telegram.Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        'Olá! Bem-vindo ao ZéUrna, seu guia para as eleições! 🗳️\n'
        'Para começar, qual o tipo de candidato que você procura (ex: Presidente, Vereador, Deputado Estadual, etc.)?'
    )
    return OBJETIVO

def main():
    if TOKEN == '7745631278:AAEv-RQLimflS-VgAzQfo2LX-aPiukHwKiE' and GOOGLE_API_KEY == 'AIzaSyDzYPpOvwRoqrfNdn7W-chgbnm8n7aV7rE':
        application = ApplicationBuilder().token(TOKEN).build()

        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, iniciar_conversa),  # Inicia com qualquer texto
            ],
            states={
                OBJETIVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_tipo)],
                LOCALIZACAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_localizacao)],
                INTERESSES: [MessageHandler(filters.TEXT & ~filters.COMMAND, buscar_candidatos)],
                NOVA_PESQUISA: [MessageHandler(filters.TEXT & ~filters.COMMAND, nova_pesquisa)],
            },
            fallbacks=[CommandHandler('cancelar', cancelar)],
        )

        application.add_handler(conv_handler)

        print("Bot ZéUrna iniciado no Telegram! 🗳️")
        application.run_polling()
    else:
        print("ERRO: Por favor, verifique se o TOKEN do Telegram e a GOOGLE_API_KEY estão configurados corretamente.")

if __name__ == '__main__':
    main()
