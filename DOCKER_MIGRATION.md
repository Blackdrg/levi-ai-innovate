# Relocating Docker Desktop Storage to Drive D (Sovereign OS Calibration)

By default, Docker Desktop for Windows stores its images and containers in your WSL 2 backend on drive C (`C:\Users\mehta\AppData\Local\Docker\wsl`). This can consume tens of gigabytes. Follow these steps to move it to drive D.

## Step 1: Shut Down Docker
1. Right-click the Docker icon in the system tray and select **Quit Docker Desktop**.
2. Open PowerShell as Administrator and ensure all WSL instances are stopped:
   ```powershell
   wsl --shutdown
   ```

## Step 2: Export Current Data
Create a temporary backup of your current Docker data:
```powershell
mkdir D:\DockerData
wsl --export docker-desktop-data D:\DockerData\docker-desktop-data.tar
```

## Step 3: Unregister Old Storage
This removes the storage from drive C:
```powershell
wsl --unregister docker-desktop-data
```

## Step 4: Import to Drive D
Import the data to the new location on drive D:
```powershell
wsl --import docker-desktop-data D:\DockerData\data D:\DockerData\docker-desktop-data.tar --version 2
```

## Step 5: Cleanup & Verification
1. Restart **Docker Desktop**.
2. Verify your images are still there by running `docker images` in a terminal.
3. Once verified, you can safely delete the temporary tar file:
   ```powershell
   Remove-Item D:\DockerData\docker-desktop-data.tar
   ```

---
> [!TIP]
> This process ensures that even the system-level Docker images (which are not controlled by the `docker-compose.yml` volumes) are entirely off your C: drive.
> 
> [!IMPORTANT]
> If you have a legacy `docker-desktop` (non-data) distribution that is also large, you can repeat the process for that as well.
