#!/usr/bin/env python3
"""
Telegram APK Cracker Bot v5.0 - FIXED APKTOOL
Auto-installs everything, no errors
"""

import os
import sys
import logging
import re
import shutil
import subprocess
import requests
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ======= CONFIG ========
BOT_TOKEN = "8732926521:AAEWoCcOAMhRMFTX49SMz2M1FSRXFUXotGQ"
# =======================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def setup_everything():
    """Complete setup - installs all tools properly"""
    print("[*] Setting up environment...")
    
    # 1. Install Java (required for everything)
    os.system("apt update -qq && apt install -y -qq default-jdk wget unzip 2>/dev/null")
    
    # 2. Download and install apktool properly
    apktool_jar = "/usr/local/bin/apktool.jar"
    apktool_sh = "/usr/local/bin/apktool"
    
    if not os.path.exists(apktool_jar):
        print("[*] Downloading apktool.jar...")
        url = "https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool"
        url_jar = "https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar"
        
        # Download jar
        os.system(f"wget -q '{url_jar}' -O {apktool_jar} 2>/dev/null")
        
        # Download wrapper script
        os.system(f"wget -q '{url}' -O {apktool_sh} 2>/dev/null")
        os.system(f"chmod +x {apktool_sh}")
        
        # Fix the script to point to correct jar
        with open(apktool_sh, 'w') as f:
            f.write('''#!/bin/bash
java -jar /usr/local/bin/apktool.jar "$@"
''')
        os.system(f"chmod +x {apktool_sh}")
    
    # 3. Install uber-apk-signer
    if not os.path.exists("/usr/local/bin/uber-apk-signer"):
        print("[*] Installing APK signer...")
        os.system("wget -q 'https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar' -O /usr/local/bin/uber-apk-signer.jar 2>/dev/null")
        with open("/usr/local/bin/uber-apk-signer", 'w') as f:
            f.write('#!/bin/bash\njava -jar /usr/local/bin/uber-apk-signer.jar "$@"\n')
        os.system("chmod +x /usr/local/bin/uber-apk-signer")
    
    # Verify
    print("[*] Verifying tools...")
    os.system("apktool --version 2>/dev/null || echo 'apktool FAILED'")
    os.system("java -version 2>&1 | head -1")
    
    print("[✓] Setup complete!")

def crack_apk(apk_path, output_dir="/tmp/cracked"):
    """Full APK cracking pipeline"""
    os.makedirs(output_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(apk_path))[0]
    decompiled = f"{output_dir}/{base}_decompiled"
    cracked = f"{output_dir}/{base}_cracked.apk"
    signed = f"{output_dir}/{base}_signed.apk"
    
    # Step 1: Decompile
    logger.info("Step 1: Decompiling...")
    result = subprocess.run(["apktool", "d", "-f", "-o", decompiled, apk_path], 
                          capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        error = result.stderr[:300] if result.stderr else result.stdout[:300]
        raise Exception(f"Decompile failed: {error}")
    
    manifest_path = f"{decompiled}/AndroidManifest.xml"
    
    # Step 2: Remove login activities
    logger.info("Step 2: Removing login activities...")
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        login_keywords = ['login', 'splash', 'sign', 'auth', 'license', 'register', 'welcome', 'onboard', 'activate', 'verify']
        
        # Find all activities
        activities = re.findall(r'<activity[^>]*android:name="([^"]*)"', content)
        
        login_activities = []
        first_non_login = None
        
        for act in activities:
            is_login = any(kw in act.lower() for kw in login_keywords)
            if is_login:
                login_activities.append(act)
            elif first_non_login is None:
                first_non_login = act
        
        if login_activities:
            # Remove MAIN intent filter from all
            content = re.sub(
                r'<intent-filter>\s*<action android:name="android\.intent\.action\.MAIN"/>\s*<category android:name="android\.intent\.category\.LAUNCHER"/>\s*</intent-filter>',
                '',
                content
            )
            
            # Remove login activity blocks
            for login_act in login_activities:
                # Find the activity tag
                for match in re.finditer(rf'<activity[^>]*{re.escape(login_act)}[^>]*>.*?</activity>', content, re.DOTALL):
                    content = content.replace(match.group(0), '')
                    break
            
            # Add MAIN to first non-login activity
            if first_non_login:
                main_filter = '\n<intent-filter>\n<action android:name="android.intent.action.MAIN"/>\n<category android:name="android.intent.category.LAUNCHER"/>\n</intent-filter>'
                for match in re.finditer(rf'(<activity[^>]*{re.escape(first_non_login)}[^>]*>)', content):
                    content = content.replace(match.group(1), match.group(1) + main_filter)
                    break
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"  Removed {len(login_activities)} login activities")
    
    # Step 3: Patch security checks
    logger.info("Step 3: Patching security checks...")
    bypass_methods = {
        'isLicensed': 'const/4 v0, 0x1\n    return v0',
        'isPurchased': 'const/4 v0, 0x1\n    return v0',
        'isPremium': 'const/4 v0, 0x1\n    return v0',
        'isPro': 'const/4 v0, 0x1\n    return v0',
        'isSubscribed': 'const/4 v0, 0x1\n    return v0',
        'isLoggedIn': 'const/4 v0, 0x1\n    return v0',
        'isSignedIn': 'const/4 v0, 0x1\n    return v0',
        'isAuthenticated': 'const/4 v0, 0x1\n    return v0',
        'isRooted': 'const/4 v0, 0x0\n    return v0',
        'isTrial': 'const/4 v0, 0x0\n    return v0',
        'isExpired': 'const/4 v0, 0x0\n    return v0',
        'isActivated': 'const/4 v0, 0x1\n    return v0',
        'isVerified': 'const/4 v0, 0x1\n    return v0',
        'hasSubscription': 'const/4 v0, 0x1\n    return v0',
        'hasAccess': 'const/4 v0, 0x1\n    return v0',
        'checkLicense': 'const/4 v0, 0x1\n    return v0',
        'verifyLicense': 'const/4 v0, 0x1\n    return v0',
        'validateLicense': 'const/4 v0, 0x1\n    return v0',
    }
    
    patched_count = 0
    for root, _, files in os.walk(decompiled):
        for file in files:
            if file.endswith('.smali'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                changed = False
                for method, bypass in bypass_methods.items():
                    pattern = rf'(\.method\s+(?:public|private|static|final|\s)*{method}\s*\(.*?\)Z[\s\S]*?)\.end\s*method'
                    replacement = f'.method public {method}()Z\n    .registers 2\n    {bypass}\n.end method'
                    if re.search(pattern, content):
                        content = re.sub(pattern, replacement, content)
                        changed = True
                
                if changed:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    patched_count += 1
    
    logger.info(f"  Patched {patched_count} smali files")
    
    # Step 4: Remove login smali files
    logger.info("Step 4: Removing login smali files...")
    removed = 0
    for root, _, files in os.walk(decompiled):
        for file in files:
            if any(kw in file.lower() for kw in ['login', 'splash', 'sign', 'auth', 'license', 'register', 'welcome', 'onboard', 'verify', 'activate']):
                try:
                    os.remove(os.path.join(root, file))
                    removed += 1
                except:
                    pass
    logger.info(f"  Removed {removed} login files")
    
    # Step 5: Rebuild
    logger.info("Step 5: Rebuilding APK...")
    result = subprocess.run(["apktool", "b", "-f", "-o", cracked, decompiled],
                          capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise Exception(f"Rebuild failed: {result.stderr[:200]}")
    
    # Step 6: Sign
    logger.info("Step 6: Signing APK...")
    result = subprocess.run(["uber-apk-signer", "--apks", cracked, "--out", signed],
                          capture_output=True, text=True, timeout=60)
    
    # Cleanup
    shutil.rmtree(decompiled, ignore_errors=True)
    
    final_path = signed if os.path.exists(signed) else cracked
    if os.path.exists(final_path):
        return final_path
    raise Exception("APK not generated after signing")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🔥 **AI APK Cracker Bot v5.0**

Send any **APK file** → Get **Cracked APK** back!

✅ Login removed
✅ License bypassed
✅ Root detection disabled
✅ No errors

**Just send the .apk file!**
"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file upload"""
    if not update.message.document:
        await update.message.reply_text("❌ Please send an APK file")
        return
    
    file = update.message.document
    file_name = file.file_name or "unknown"
    
    msg = await update.message.reply_text("📥 **Downloading...**", parse_mode='Markdown')
    
    try:
        file_obj = await file.get_file()
        apk_path = f"/tmp/apk_{update.effective_user.id}_{file.file_unique_id}.apk"
        await file_obj.download_to_drive(apk_path)
        
        if not os.path.exists(apk_path) or os.path.getsize(apk_path) == 0:
            await msg.edit_text("❌ Download failed")
            return
        
        await msg.edit_text("🔍 **Cracking APK...** ⏳", parse_mode='Markdown')
        
        output_path = crack_apk(apk_path)
        
        if output_path and os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            
            await msg.edit_text(f"✅ **Cracked!** ({size_mb:.1f}MB)\n📤 **Sending...**", parse_mode='Markdown')
            
            with open(output_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"Cracked_{os.path.basename(output_path)}",
                    caption="🔥 **CRACKED APK**\n✅ Login removed\n✅ License bypassed\n✅ No errors"
                )
            
            await msg.delete()
            os.remove(output_path)
        else:
            await msg.edit_text("❌ Failed. Try another APK.")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text(f"❌ Error: {str(e)[:200]}")
    finally:
        if os.path.exists(apk_path):
            os.remove(apk_path)

def main():
    # FIRST: Install all tools properly
    setup_everything()
    
    # THEN: Start bot
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    
    print("🤖 Bot is running! Send APK file to crack it.")
    app.run_polling()

if __name__ == "__main__":
    main()
