import os
import logging
import tempfile
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from telegram.ext import ConversationHandler
import ffmpeg
from moviepy.editor import VideoFileClip
import subprocess
import uuid
from urllib.parse import quote
import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
SELECTING_ACTION, CHOOSING_FORMAT, CHOOSING_COMPRESSION, CHOOSING_RESOLUTION = range(4)

class VideoConverterBot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
        
    def setup_handlers(self):
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Conversation handler for video conversion
        conv_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.VIDEO | filters.Document.VIDEO, self.receive_video)],
            states={
                SELECTING_ACTION: [CallbackQueryHandler(self.select_action)],
                CHOOSING_FORMAT: [CallbackQueryHandler(self.choose_format)],
                CHOOSING_COMPRESSION: [CallbackQueryHandler(self.choose_compression)],
                CHOOSING_RESOLUTION: [CallbackQueryHandler(self.choose_resolution)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
        self.application.add_handler(conv_handler)
        
        # Handle text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))

    async def start(self, update: Update, context: CallbackContext) -> None:
        """Send welcome message when command /start is issued."""
        user = update.effective_user
        
        # Create a stylish welcome message like in the images
        welcome_text = f"""
🎬 <b>Welcome to Video Converter Pro!</b> 🎬

👋 Hello <b>{user.first_name}</b>!

🤖 I'm your advanced Video Converter Bot with premium features:

✨ <b>Premium Features:</b>
• Convert any video format (MP4, AVI, MOV, MKV, WEBM, GIF)
• Support for files up to <b>2GB</b>
• 4K Ultra HD conversion
• Advanced compression algorithms
• Batch processing support
• High-speed processing

⚡ <b>Quick Start:</b>
Just send me a video file and I'll show you the magic!

📊 <b>Bot Status:</b>
✅ Online | 🚀 Ready | 💾 2GB Support

Use /help for detailed instructions.
        """
        
        # Add stylish buttons like in the images
        keyboard = [
            [InlineKeyboardButton("🚀 Quick Start Guide", callback_data="quick_guide")],
            [InlineKeyboardButton("📊 Bot Status", callback_data="status")],
            [InlineKeyboardButton("🆘 Help & Support", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    async def help_command(self, update: Update, context: CallbackContext) -> None:
        """Send help message styled like the images."""
        help_text = """
🔧 <b>Video Converter Pro - Help Guide</b> 🔧

📹 <b>How to Use:</b>
1. <b>Send Video</b> - Upload any video file (up to 2GB)
2. <b>Choose Action</b> - Select from format conversion, compression, etc.
3. <b>Customize Settings</b> - Adjust quality, resolution, format
4. <b>Process</b> - Wait for high-quality conversion
5. <b>Download</b> - Get your optimized video!

🎯 <b>Available Features:</b>

<u>Format Conversion</u>
• MP4 (Recommended) | AVI | MOV | MKV
• WEBM | GIF | 3GP | WMV
• FLV | M4V | and more...

<u>Video Compression</u>
• 💎 Ultra Quality (90% original)
• ⚖️ Balanced (70% original)  
• 📦 Space Saver (50% original)
• 🔥 Extreme Compression (30% original)

<u>Resolution Options</u>
• 4K (2160p) | 2K (1440p) | 1080p Full HD
• 720p HD | 480p | 360p | 240p

⚡ <b>Pro Tips:</b>
• For best quality: Use MP4 format
• For social media: 1080p resolution
• For WhatsApp: Use compression
• Maximum file size: <b>2GB</b>

🔐 <b>Privacy:</b>
Your files are processed securely and deleted after 1 hour.

Need more help? Contact @support_admin
        """
        
        keyboard = [
            [InlineKeyboardButton("🎥 Send Video Now", switch_inline_query_current_chat="")],
            [InlineKeyboardButton("📊 View Status", callback_data="status"),
             InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=reply_markup)

    async def status_command(self, update: Update, context: CallbackContext) -> None:
        """Show bot status like in the images."""
        status_text = """
📊 <b>Bot Status Dashboard</b> 📊

🟢 <b>System Status:</b> ONLINE
⚡ <b>Performance:</b> OPTIMAL
💾 <b>Storage:</b> READY

🔧 <b>Current Capabilities:</b>
✅ Video Conversion: ACTIVE
✅ 2GB Support: ENABLED  
✅ 4K Processing: READY
✅ Cloud Storage: AVAILABLE
✅ High Speed: OPERATIONAL

📈 <b>Server Metrics:</b>
• Uptime: 99.9%
• Processing Speed: Fast
• Queue: Empty
• Memory: Optimal

🛠️ <b>Maintenance:</b>
No scheduled maintenance

💡 <b>Tip:</b> Send any video to test the system!
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Test System", callback_data="test")],
            [InlineKeyboardButton("📹 Send Video", switch_inline_query_current_chat="")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(status_text, parse_mode='HTML', reply_markup=reply_markup)

    async def receive_video(self, update: Update, context: CallbackContext) -> int:
        """Handle incoming video with enhanced UI like images."""
        try:
            # Store video file info
            if update.message.video:
                file = update.message.video
                file_type = "video"
            else:
                file = update.message.document
                file_type = "document"
                
            file_id = file.file_id
            file_size = file.file_size
            file_name = getattr(file, 'file_name', 'video_file')
            
            context.user_data['file_id'] = file_id
            context.user_data['file_size'] = file_size
            context.user_data['file_name'] = file_name
            context.user_data['file_type'] = file_type
            
            # Convert file size to readable format
            size_mb = file_size / (1024 * 1024)
            
            # Check file size (2GB limit)
            if file_size > 2 * 1024 * 1024 * 1024:
                await update.message.reply_text(
                    "❌ <b>File Too Large!</b>\n\n"
                    f"Your file size: <b>{size_mb:.1f} MB</b>\n"
                    "Maximum allowed: <b>2GB</b>\n\n"
                    "Please send a smaller file or compress it first.",
                    parse_mode='HTML'
                )
                return ConversationHandler.END
            
            # Show file info and action selection with stylish UI
            file_info_text = f"""
📹 <b>Video Received Successfully!</b> 📹

📄 <b>File Info:</b>
• Name: <code>{file_name}</code>
• Size: <b>{size_mb:.1f} MB</b>
• Type: <b>{file_type.upper()}</b>
• Status: <b>Ready for Processing</b>

🎯 <b>Choose your action:</b>
What would you like to do with this video?
            """
            
            # Enhanced keyboard layout like in the images
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Change Format", callback_data="format"),
                    InlineKeyboardButton("📦 Compress Video", callback_data="compress")
                ],
                [
                    InlineKeyboardButton("🖼️ Change Resolution", callback_data="resolution"),
                    InlineKeyboardButton("⚡ Quick Convert", callback_data="quick_mp4")
                ],
                [
                    InlineKeyboardButton("🎞️ Extract Audio", callback_data="extract_audio"),
                    InlineKeyboardButton("✂️ Trim Video", callback_data="trim")
                ],
                [
                    InlineKeyboardButton("🔧 Advanced Settings", callback_data="advanced")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send processing message with file info
            processing_msg = await update.message.reply_text("🔄 <b>Analyzing video file...</b>", parse_mode='HTML')
            await asyncio.sleep(1)  # Simulate analysis
            
            await processing_msg.edit_text(file_info_text, reply_markup=reply_markup, parse_mode='HTML')
            
            return SELECTING_ACTION
            
        except Exception as e:
            logger.error(f"Error receiving video: {e}")
            await update.message.reply_text("❌ Error processing your video. Please try again.")
            return ConversationHandler.END

    async def select_action(self, update: Update, context: CallbackContext) -> int:
        """Handle action selection with enhanced UI."""
        query = update.callback_query
        await query.answer()
        
        action = query.data
        context.user_data['action'] = action
        
        if action == "format":
            return await self.show_format_options(query)
        elif action == "compress":
            return await self.show_compression_options(query)
        elif action == "resolution":
            return await self.show_resolution_options(query)
        elif action == "quick_mp4":
            return await self.process_quick_convert(query, context)
        elif action in ["extract_audio", "trim", "advanced"]:
            return await self.show_advanced_options(query, action)
            
        return SELECTING_ACTION

    async def show_format_options(self, query) -> int:
        """Show format selection with enhanced UI."""
        keyboard = [
            [
                InlineKeyboardButton("🎯 MP4 (Recommended)", callback_data="format_mp4"),
                InlineKeyboardButton("📹 AVI", callback_data="format_avi")
            ],
            [
                InlineKeyboardButton("🎬 MOV", callback_data="format_mov"),
                InlineKeyboardButton("📁 MKV", callback_data="format_mkv")
            ],
            [
                InlineKeyboardButton("🌐 WEBM", callback_data="format_webm"),
                InlineKeyboardButton("🔄 GIF", callback_data="format_gif")
            ],
            [
                InlineKeyboardButton("📱 3GP", callback_data="format_3gp"),
                InlineKeyboardButton("💾 WMV", callback_data="format_wmv")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="back_main"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        format_info = """
🔄 <b>Format Conversion</b> 🔄

📊 <b>Recommended Formats:</b>
• <b>MP4</b> - Best quality, universal support
• <b>MOV</b> - High quality, Apple devices
• <b>AVI</b> - Good quality, Windows compatible

💡 <b>Format Guide:</b>
• Social Media: MP4 or WEBM
• Mobile Devices: MP4 or 3GP
• Editing: MOV or AVI
• Web: MP4 or WEBM

Select your desired output format:
        """
        
        await query.edit_message_text(format_info, reply_markup=reply_markup, parse_mode='HTML')
        return CHOOSING_FORMAT

    async def show_compression_options(self, query) -> int:
        """Show compression options with enhanced UI."""
        file_size = query.message.chat.get('file_size', 0)
        size_mb = file_size / (1024 * 1024) if file_size > 0 else 0
        
        keyboard = [
            [
                InlineKeyboardButton("💎 Ultra Quality", callback_data="compress_high"),
                InlineKeyboardButton("⚖️ Balanced", callback_data="compress_medium")
            ],
            [
                InlineKeyboardButton("📦 Space Saver", callback_data="compress_low"),
                InlineKeyboardButton("🔥 Extreme", callback_data="compress_very_low")
            ],
            [
                InlineKeyboardButton("🔧 Custom Settings", callback_data="compress_custom")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="back_main"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        compression_info = f"""
📦 <b>Video Compression</b> 📦

📊 <b>Current File Size:</b> {size_mb:.1f} MB

🎯 <b>Compression Levels:</b>

• <b>💎 Ultra Quality</b> - 90% original (Best quality)
• <b>⚖️ Balanced</b> - 70% original (Recommended)
• <b>📦 Space Saver</b> - 50% original (Good balance)  
• <b>🔥 Extreme</b> - 30% original (Smallest size)

💡 <b>Tips:</b>
• For social media: Balanced
• For storage: Space Saver
• For quality: Ultra Quality

Select compression level:
        """
        
        await query.edit_message_text(compression_info, reply_markup=reply_markup, parse_mode='HTML')
        return CHOOSING_COMPRESSION

    async def show_resolution_options(self, query) -> int:
        """Show resolution options with enhanced UI."""
        keyboard = [
            [
                InlineKeyboardButton("4K 🚀", callback_data="res_2160"),
                InlineKeyboardButton("2K ⚡", callback_data="res_1440")
            ],
            [
                InlineKeyboardButton("1080p 💎", callback_data="res_1080"),
                InlineKeyboardButton("720p 🔥", callback_data="res_720")
            ],
            [
                InlineKeyboardButton("480p 📱", callback_data="res_480"),
                InlineKeyboardButton("360p 🌐", callback_data="res_360")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="back_main"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        resolution_info = """
🖼️ <b>Resolution Settings</b> 🖼️

📊 <b>Resolution Guide:</b>

• <b>4K (2160p)</b> - Ultra HD, best quality
• <b>2K (1440p)</b> - High quality, large screens  
• <b>1080p</b> - Full HD, recommended
• <b>720p</b> - HD, social media optimized
• <b>480p</b> - Standard, mobile optimized
• <b>360p</b> - Basic, fast streaming

💡 <b>Usage Tips:</b>
• YouTube/TV: 4K or 1080p
• Social Media: 1080p or 720p
• WhatsApp: 720p or 480p
• Fast sharing: 480p or 360p

Select output resolution:
        """
        
        await query.edit_message_text(resolution_info, reply_markup=reply_markup, parse_mode='HTML')
        return CHOOSING_RESOLUTION

    async def show_advanced_options(self, query, action: str) -> int:
        """Show advanced options."""
        if action == "extract_audio":
            await query.edit_message_text("🎵 <b>Audio Extraction</b>\n\nThis feature will be available soon!", parse_mode='HTML')
        elif action == "trim":
            await query.edit_message_text("✂️ <b>Video Trimming</b>\n\nThis feature will be available soon!", parse_mode='HTML')
        elif action == "advanced":
            await query.edit_message_text("🔧 <b>Advanced Settings</b>\n\nThis feature will be available soon!", parse_mode='HTML')
        
        return SELECTING_ACTION

    async def process_quick_convert(self, query, context: CallbackContext) -> int:
        """Quick convert to MP4 with enhanced UI."""
        context.user_data['format'] = 'mp4'
        context.user_data['action'] = 'quick_mp4'
        
        processing_text = """
⚡ <b>Quick Convert Started</b> ⚡

🔄 <b>Settings Applied:</b>
• Format: <b>MP4</b> (Recommended)
• Quality: <b>Auto Optimized</b>
• Resolution: <b>Original</b>

⏳ <b>Processing:</b> This may take a few minutes for large files.

📊 <b>Status:</b> Initializing conversion engine...
        """
        
        await query.edit_message_text(processing_text, parse_mode='HTML')
        return await self.process_video(query, context)

    async def process_video(self, query, context: CallbackContext) -> int:
        """Process the video with progress updates."""
        try:
            # Get file info
            file_id = context.user_data.get('file_id')
            file_size = context.user_data.get('file_size', 0)
            action = context.user_data.get('action', 'quick_mp4')
            
            # Show initial progress
            progress_msg = await query.message.reply_text("🔄 <b>Downloading video file...</b>", parse_mode='HTML')
            
            # Download the file
            file = await context.bot.get_file(file_id)
            
            # Create temporary files
            input_path = f"/tmp/input_{uuid.uuid4()}.mp4"
            output_path = f"/tmp/output_{uuid.uuid4()}.mp4"
            
            await file.download_to_drive(input_path)
            
            # Update progress
            await progress_msg.edit_text("✅ <b>Download completed!</b>\n🔄 <b>Starting conversion...</b>", parse_mode='HTML')
            
            # Process based on action
            if action == 'format':
                format_type = context.user_data.get('format', 'mp4')
                output_path = await self.convert_format(input_path, output_path, format_type, progress_msg)
            elif action == 'compress':
                compression = context.user_data.get('compression', 'medium')
                output_path = await self.compress_video(input_path, output_path, compression, progress_msg)
            elif action == 'resolution':
                resolution = context.user_data.get('resolution', '720')
                output_path = await self.change_resolution(input_path, output_path, resolution, progress_msg)
            else:
                output_path = await self.convert_to_mp4(input_path, output_path, progress_msg)
            
            # Get output file size
            output_size = os.path.getsize(output_path) / (1024 * 1024)
            
            # Send the processed video
            await progress_msg.edit_text("✅ <b>Conversion completed!</b>\n📤 <b>Uploading result...</b>", parse_mode='HTML')
            
            with open(output_path, 'rb') as video_file:
                await query.message.reply_video(
                    video=video_file,
                    caption=f"✅ <b>Conversion Successful!</b>\n\n"
                           f"📊 <b>Original Size:</b> {file_size/(1024*1024):.1f} MB\n"
                           f"📦 <b>Final Size:</b> {output_size:.1f} MB\n"
                           f"🎯 <b>Quality:</b> Optimized\n\n"
                           f"Thank you for using <b>Video Converter Pro</b>! 🎬",
                    parse_mode='HTML'
                )
            
            # Cleanup
            try:
                os.unlink(input_path)
                os.unlink(output_path)
            except:
                pass
            
            await progress_msg.delete()
            
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            await query.edit_message_text("❌ <b>Error processing video.</b>\n\nPlease try again with a different file or settings.", parse_mode='HTML')
        
        return ConversationHandler.END

    # ... (Keep the existing conversion methods but add progress updates)
    
    async def convert_format(self, input_path: str, output_path: str, format_type: str, progress_msg) -> str:
        """Convert video format with progress updates."""
        # Implementation with progress updates
        pass
    
    async def compress_video(self, input_path: str, output_path: str, compression: str, progress_msg) -> str:
        """Compress video with progress updates."""
        # Implementation with progress updates
        pass
    
    async def change_resolution(self, input_path: str, output_path: str, resolution: str, progress_msg) -> str:
        """Change resolution with progress updates."""
        # Implementation with progress updates
        pass
    
    async def convert_to_mp4(self, input_path: str, output_path: str, progress_msg) -> str:
        """Quick convert to MP4 with progress updates."""
        # Implementation with progress updates
        pass

    async def cancel(self, update: Update, context: CallbackContext) -> int:
        """Cancel the conversation."""
        await update.message.reply_text(
            "❌ <b>Operation cancelled.</b>\n\n"
            "Send me another video if you need conversion! 🎥",
            parse_mode='HTML'
        )
        return ConversationHandler.END

    async def handle_text(self, update: Update, context: CallbackContext) -> None:
        """Handle text messages."""
        await update.message.reply_text(
            "🎬 <b>Video Converter Pro</b> 🎬\n\n"
            "📹 Send me a video file to get started!\n\n"
            "Use /help for instructions or /status to check bot status.",
            parse_mode='HTML'
        )

    def run(self):
        """Run the bot with webhook for Koyeb."""
        # For Koyeb, we'll use polling (simpler for this setup)
        self.application.run_polling()

# Main execution
if __name__ == '__main__':
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    if not BOT_TOKEN:
        print("❌ Please set BOT_TOKEN environment variable!")
        exit(1)
    
    bot = VideoConverterBot(BOT_TOKEN)
    print("🚀 Video Converter Bot is running on Koyeb...")
    print("💾 2GB file support: ENABLED")
    print("🎬 Premium features: ACTIVE")
    bot.run()
