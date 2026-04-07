import os
import logging
import asyncio
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from models import Database
from api_client import APIClient

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 환경변수 로드
load_dotenv()

# 상수 정의
REGIONS = ["전국", "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시", "대전광역시", "울산광역시", "세종특별자치시", "강원도", "경기도", "경상남도", "경상북도", "전라남도", "전라북도", "충청남도", "충청북도", "제주특별자치도"]
CATEGORIES = ["사업화", "기술개발(R&D)", "시설·공간·보육", "멘토링·컨설팅·교육", "글로벌", "인력", "융자·보증", "행사·네트워크", "창업교육", "판로·해외진출", "정책자금"]
TARGETS = ["청소년", "대학생", "일반인", "대학", "연구기관", "일반기업", "1인 창조기업"]
HISTORIES = ["예비창업자", "1년미만", "2년미만", "3년미만", "5년미만", "7년미만", "10년미만"]

# 전역 객체
db = Database()
api = APIClient(
    bizinfo_key=os.getenv("BIZINFO_API_KEY"),
    kstartup_key=os.getenv("KSTARTUP_API_KEY"),
    openai_key=os.getenv("OPENAI_API_KEY")
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start 명령어 처리"""
    chat_id = update.effective_chat.id
    db.add_user(chat_id)
    
    keyboard = [
        [InlineKeyboardButton("🔍 공고 검색", callback_data='search_menu')],
        [InlineKeyboardButton("🔔 알림 설정", callback_data='settings_menu')],
        [InlineKeyboardButton("❓ 도움말", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = (
        "🇰🇷 **정부지원사업 알림 봇**\n\n"
        "기업마당과 K-스타트업의 공고를 한눈에 확인하세요!\n"
        "원하시는 기능을 아래 버튼에서 선택해주세요."
    )
    
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """검색 메뉴 표시"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📝 키워드로 검색", callback_data='search_keyword')],
        [InlineKeyboardButton("📍 지역별 공고", callback_data='filter_region')],
        [InlineKeyboardButton("📂 분야별 공고", callback_data='filter_category')],
        [InlineKeyboardButton("⬅️ 뒤로가기", callback_data='back_to_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("검색 방식을 선택해주세요.", reply_markup=reply_markup)

async def search_keyword_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """키워드 입력 안내"""
    query = update.callback_query
    await query.answer()
    context.user_data['state'] = 'AWAITING_KEYWORD'
    await query.edit_message_text("검색하실 키워드를 입력해주세요. (예: 인공지능, 수출, 경기)")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """메시지 처리 (키워드 검색 등)"""
    state = context.user_data.get('state')
    if state == 'AWAITING_KEYWORD':
        keyword = update.message.text
        context.user_data['state'] = None
        await search_by_keyword(update, context, keyword)
    else:
        await update.message.reply_text("알 수 없는 명령입니다. /start 를 입력해 메뉴를 확인하세요.")

async def search_by_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE, keyword: str):
    """키워드로 공고 검색 실행"""
    loading_msg = await update.message.reply_text(f"'{keyword}' 키워드로 공고를 검색 중입니다...")
    
    results = api.fetch_bizinfo(hashtags=keyword, search_cnt=5)
    
    if not results:
        await loading_msg.edit_text(f"'{keyword}'에 대한 검색 결과가 없습니다.")
        return

    await loading_msg.delete()
    
    for item in results:
        title = item.get('pblancNm') or item.get('title')
        agency = item.get('jrsdInsttNm') or item.get('author', '기관정보없음')
        pblanc_id = item.get('pblancId') or item.get('seq')
        url = item.get('pblancUrl') or item.get('link')
        
        # 상세 요약을 위한 데이터 저장
        context.bot_data[f"summary_{pblanc_id}"] = item.get('bsnsSumryCn') or item.get('description', '')
        
        keyboard = []
        # OpenAI 클라이언트가 활성화된 경우에만 요약 버튼 노출
        if api.openai_client:
            keyboard.append([InlineKeyboardButton("🤖 AI 요약", callback_data=f"summarize_{pblanc_id}")])
        
        keyboard.append([InlineKeyboardButton("🔗 원문 보기", url=url)])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        msg = f"📌 **{title}**\n🏛 {agency}\n"
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def summarize_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI 요약 버튼 클릭 처리"""
    query = update.callback_query
    pblanc_id = query.data.replace("summarize_", "")
    content = context.bot_data.get(f"summary_{pblanc_id}")
    
    if not api.openai_client:
        await query.answer("현재 요약 기능을 사용할 수 없습니다. (OpenAI API 키 설정 확인 필요)", show_alert=True)
        return

    await query.answer("AI 요약을 생성 중입니다...")
    
    original_text = query.message.text
    title = original_text.split('\n')[0].replace('📌 ', '')
    
    summary = api.summarize_announcement(title, content)
    
    keyboard = query.message.reply_markup.inline_keyboard
    new_keyboard = [row for row in keyboard if not any(btn.callback_data == query.data for btn in row)]
    reply_markup = InlineKeyboardMarkup(new_keyboard)
    
    await query.edit_message_text(
        f"{original_text}\n\n✨ **AI 요약**\n{summary}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """알림 설정 메뉴"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📍 지역 설정", callback_data='set_region')],
        [InlineKeyboardButton("📂 분야 설정", callback_data='set_category')],
        [InlineKeyboardButton("👤 대상 설정", callback_data='set_target')],
        [InlineKeyboardButton("📈 업력 설정", callback_data='set_history')],
        [InlineKeyboardButton("⬅️ 뒤로가기", callback_data='back_to_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    chat_id = update.effective_chat.id
    settings = db.get_user_settings(chat_id)
    region = settings.get('region', '미설정')
    category = settings.get('category', '미설정')
    target = settings.get('target', '미설정')
    history = settings.get('history', '미설정')
    
    msg = (
        "🔔 **알림 설정**\n\n"
        "새로운 공고가 올라왔을 때 알려드릴 조건을 설정하세요.\n"
        f"📍 지역: {region}\n"
        f"📂 분야: {category}\n"
        f"👤 대상: {target}\n"
        f"📈 업력: {history}\n"
    )
    await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def set_filter_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """필터 옵션 선택 (지역, 분야 등)"""
    query = update.callback_query
    filter_type = query.data.replace('set_', '')
    await query.answer()
    
    options = []
    if filter_type == 'region': options = REGIONS
    elif filter_type == 'category': options = CATEGORIES
    elif filter_type == 'target': options = TARGETS
    elif filter_type == 'history': options = HISTORIES
    
    keyboard = []
    for i in range(0, len(options), 2):
        row = [InlineKeyboardButton(options[i], callback_data=f"save_{filter_type}_{options[i]}")]
        if i+1 < len(options):
            row.append(InlineKeyboardButton(options[i+1], callback_data=f"save_{filter_type}_{options[i+1]}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("⬅️ 뒤로가기", callback_data='settings_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"설정할 {filter_type}을 선택해주세요.", reply_markup=reply_markup)

async def save_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """사용자 설정 저장"""
    query = update.callback_query
    _, filter_type, value = query.data.split('_', 2)
    chat_id = update.effective_chat.id
    
    db.set_user_setting(chat_id, filter_type, value)
    
    # 설정 완료 팝업 알림 (짧은 메시지)
    await query.answer(f"{value} 설정 완료!")
    
    # 설정 완료 후 메뉴를 갱신하면서 안내 문구 추가
    keyboard = [
        [InlineKeyboardButton("📍 지역 설정", callback_data='set_region')],
        [InlineKeyboardButton("📂 분야 설정", callback_data='set_category')],
        [InlineKeyboardButton("👤 대상 설정", callback_data='set_target')],
        [InlineKeyboardButton("📈 업력 설정", callback_data='set_history')],
        [InlineKeyboardButton("⬅️ 뒤로가기", callback_data='back_to_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    settings = db.get_user_settings(chat_id)
    msg = (
        "✅ **알림 설정이 완료되었습니다.**\n"
        "조건에 맞는 새 공고가 올라오면 알려드릴게요!\n\n"
        f"📍 지역: {settings.get('region', '미설정')}\n"
        f"📂 분야: {settings.get('category', '미설정')}\n"
        f"👤 대상: {settings.get('target', '미설정')}\n"
        f"📈 업력: {settings.get('history', '미설정')}\n"
    )
    await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def check_new_announcements(context: ContextTypes.DEFAULT_TYPE):
    """새 공고 체크 및 알림 전송 (JobQueue용)"""
    logger.info("Checking for new announcements...")
    
    latest_items = api.fetch_bizinfo(search_cnt=20)
    
    for item in latest_items:
        pblanc_id = item.get('pblancId') or item.get('seq')
        title = item.get('pblancNm') or item.get('title')
        
        if not db.is_notified(pblanc_id):
            db.add_notification(pblanc_id, title, item.get('pubDate', ''))
            
            users = db.get_all_users()
            for chat_id in users:
                settings = db.get_user_settings(chat_id)
                
                # 필터링 로직 강화
                region_match = not settings.get('region') or settings.get('region') in (item.get('hashTags', '') + item.get('title', ''))
                category_match = not settings.get('category') or settings.get('category') in (item.get('lcategory', '') + item.get('title', ''))
                # 업력 필터링 (제목이나 해시태그에서 검색)
                history_match = not settings.get('history') or settings.get('history') in (item.get('title', '') + item.get('hashTags', ''))
                
                if region_match and category_match and history_match:
                    try:
                        url = item.get('pblancUrl') or item.get('link')
                        msg = f"🆕 **새로운 공고 알림!**\n\n📌 {title}\n🏛 {item.get('jrsdInsttNm', '기관정보없음')}"
                        keyboard = [[InlineKeyboardButton("🔗 원문 보기", url=url)]]
                        await context.bot.send_message(chat_id, msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
                    except Exception as e:
                        logger.error(f"Failed to send notification to {chat_id}: {e}")

def main():
    """봇 실행"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set.")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(start, pattern='back_to_start'))
    application.add_handler(CallbackQueryHandler(search_menu, pattern='search_menu'))
    application.add_handler(CallbackQueryHandler(search_keyword_prompt, pattern='search_keyword'))
    application.add_handler(CallbackQueryHandler(summarize_callback, pattern='summarize_'))
    application.add_handler(CallbackQueryHandler(settings_menu, pattern='settings_menu'))
    application.add_handler(CallbackQueryHandler(set_filter_options, pattern='set_'))
    application.add_handler(CallbackQueryHandler(save_setting, pattern='save_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.job_queue.run_repeating(check_new_announcements, interval=3600, first=10)

    logger.info("Bot started with JobQueue and enhanced features...")
    application.run_polling()

if __name__ == '__main__':
    main()
