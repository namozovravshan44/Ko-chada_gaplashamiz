# Ko'chada Gaplashamiz — Sotuv Boti

## Nima qiladi

- `/start` bosilganda video + matn yuboradi (admin buni keyinchalik o'zgartira oladi)
- **🎁 Bepul namuna** — ism-familiya va telefon raqamini so'rab, lead sifatida bazaga saqlaydi
- **💳 Sotib olish** — karta raqamini ko'rsatadi, keyin foydalanuvchi to'lov chekini (rasm) yuboradi
- Chek avtomatik ravishda admin/operatorlarga "Tasdiqlash / Rad etish" tugmalari bilan yuboriladi
- Har bir start bosgan foydalanuvchi (ID, username, ism, telefon, sana) bazaga yoziladi

## Buyruqlar

**Super admin (`SUPER_ADMIN_IDS` ichida bo'lganlar):**
- `/stats` — to'liq statistika
- `/export` — barcha foydalanuvchilarni CSV qilib yuklab olish
- `/broadcast` — barchaga xabar yuborish (matn/rasm/video bo'lishi mumkin)
- `/setstart` — `/start` dagi video va matnni yangilash
- `/setbook` — kitobning PDF va audio fayllarini yuklash (to'lov tasdiqlanganda avtomatik yuboriladi). Fayllarni birma-bir yuboring, so'ng `/donebook` deb yozing
- `/bookfiles` — hozir yuklangan kitob fayllari ro'yxati
- `/addoperator <user_id>` — operator qo'shish
- `/removeoperator <user_id>` — operatorni o'chirish
- `/operators` — operatorlar ro'yxati
- `/adminhelp` — buyruqlar ro'yxati

**Operator:**
- `/leads` — qisqacha statistika
- Chek kelganda "✅ Tasdiqlash" yoki "❌ Rad etish" tugmasini bosish

## O'zingizning Telegram ID'ingizni bilish

@userinfobot ga yozib, u sizga ID raqamingizni beradi. Shu raqamni `SUPER_ADMIN_IDS` ga qo'ying.

## Lokal ishga tushirish

```bash
pip install -r requirements.txt
cp .env.example .env
# .env faylini o'zingizning BOT_TOKEN va SUPER_ADMIN_IDS bilan to'ldiring
python main.py
```

## Railway'ga joylash

1. Yangi GitHub repo yarating va shu papkadagi barcha fayllarni shu repoga yuklang
2. Railway.app'da **New Project → Deploy from GitHub repo** ni tanlang
3. Repo'ni tanlang
4. **Variables** bo'limiga o'ting va quyidagilarni qo'shing:
   - `BOT_TOKEN` — @BotFather'dan olingan token
   - `SUPER_ADMIN_IDS` — sizning Telegram ID'ingiz (vergul bilan bir nechtasini yozish mumkin)
   - `APPROVAL_CHAT_ID` — cheklar kelib tushadigan chat ID (o'zingizning shaxsiy ID yoki alohida guruh)
   - `CARD_NUMBER`, `CARD_OWNER`, `BOOK_PRICE` — kerak bo'lsa o'zgartiring
5. **Settings → Start Command** ni `python main.py` qilib qo'ying
6. Deploy tugmasini bosing — bot avtomatik ishga tushadi

> Eslatma: `bot_database.db` fayli Railway'ning konteyner fayl tizimida saqlanadi. Agar konteyner qayta ishga tushirilsa (redeploy), baza saqlanib qoladi, lekin agar butunlay yangi service yaratsangiz, baza tozalanadi. Uzoq muddatda ma'lumotlarni yo'qotmaslik uchun Railway'ning Volume funksiyasidan foydalanish yoki keyinchalik PostgreSQL'ga o'tish tavsiya qilinadi.

## Kitob fayllarini yuklash (birinchi marta ishga tushirgach)

Bot ishga tushgach, o'zingiz botga yozing:
1. `/setbook`
2. PDF faylni dokument sifatida yuboring
3. Audio fayllarni birma-bir yuboring (agar bir nechta bo'lsa)
4. `/donebook`

Shundan keyin har safar kimdir to'lov qilib, chek tasdiqlansa, bot shu fayllarni avtomatik o'sha foydalanuvchiga yuboradi.

## Keyingi qadamlar uchun g'oyalar

- Follow-up: agar 24/48 soatda xarid qilinmasa, avtomatik eslatma yuborish (APScheduler yordamida)
- Referral tizimi
- Konversiya funneli (start → lead → chek → xarid) foizlarda ko'rsatish
