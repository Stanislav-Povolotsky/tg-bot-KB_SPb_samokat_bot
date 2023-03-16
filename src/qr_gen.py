# -------------------------------------------------------------------------------------------------
# (C) Stanislav Povolotsky, 2023
# https://github.com/Stanislav-Povolotsky/tg-bot-KB_SPb_samokat_bot
# -------------------------------------------------------------------------------------------------
import qrcode
import io

def gen_qr_code_for_text(text):
  qr = qrcode.QRCode(
      version=1,
      error_correction=qrcode.constants.ERROR_CORRECT_M,
      box_size=10,
      border=4,
  )
  qr.add_data(text, optimize = 0)
  qr.make(fit=True)
  
  img = qr.make_image(back_color=(255, 255, 255), fill_color=(0, 0, 0))
  
  mem_img_file = io.BytesIO()
  img.save(mem_img_file, format='PNG')
  mem_img_file.seek(0)
  return mem_img_file
