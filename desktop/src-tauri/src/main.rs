#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use tauri::{
    CustomMenuItem, Manager, SystemTray, SystemTrayEvent, SystemTrayMenu, SystemTrayMenuItem,
};
use tauri_plugin_shell::ShellExt;
use std::process::Command;

#[tauri::command]
async def execute_system_command(cmd: String) -> Result<String, String> {
    // Basic safety check: don't allow potentially destructive commands without manual parsing
    // In a real production app, this would use an allow-list or LLM-based validation
    match cmd.as_str() {
        "chrome" => {
            Command::new("cmd").args(&["/C", "start chrome"]).spawn().map_err(|e| e.to_string())?;
            Ok("Opened Chrome".to_string())
        },
        "notepad" => {
            Command::new("cmd").args(&["/C", "start notepad"]).spawn().map_err(|e| e.to_string())?;
            Ok("Opened Notepad".to_string())
        },
        _ => {
            // Forward to PowerShell for generic commands (with caution)
            let output = Command::new("powershell")
                .args(&["-Command", &cmd])
                .output()
                .map_err(|e| e.to_string())?;
            Ok(String::from_utf8_lossy(&output.stdout).to_string())
        }
    }
}

#[tauri::command]
fn toggle_palette(app_handle: tauri::AppHandle) {
    let window = app_handle.get_window("palette").unwrap();
    if window.is_visible().unwrap() {
        window.hide().unwrap();
    } else {
        window.show().unwrap();
        window.set_focus().unwrap();
    }
}

fn main() {
    let tray_menu = SystemTrayMenu::new()
        .add_item(CustomMenuItem::new("show".to_string(), "Show Dashboard"))
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(CustomMenuItem::new("quit".to_string(), "Quit LEVI"));

    let system_tray = SystemTray::new().with_menu(tray_menu);

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .system_tray(system_tray)
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
                "quit" => {
                    std::process::exit(0);
                }
                "show" => {
                    let window = app.get_window("main").unwrap();
                    window.show().unwrap();
                    window.set_focus().unwrap();
                }
                _ => {}
            },
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![execute_system_command, toggle_palette])
        .setup(|app| {
            // Start the Python Sidecar
            let sidecar_command = app.shell().sidecar("levi-core").map_err(|e| {
                println!("Failed to create sidecar command: {}", e);
                e
            })?;
            
            let (mut _rx, mut _child) = sidecar_command.spawn().map_err(|e| {
                println!("Failed to spawn sidecar: {}", e);
                e
            })?;

            println!("LEVI Backend Sidecar started.");

            // Register Global Hotkey (Alt + Space)
            let app_handle = app.handle();
            // Note: In Tauri v2, global shortcuts are often handled by a plugin
            // For now, we'll assume the frontend captures the event or use the shortcut plugin
            
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
