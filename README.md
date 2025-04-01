Template repository for using Cursor on the RU HPC cluster.

For best results, you will want to use the new Rocky 9 server (login05), which is compatible with the newest version of Cursor. To get access to Rocky 9, email it_hpc@rockefeller.edu and request onboarding to the Rocky 9 system. Rocky 9 can be accessed by login05-hpc.rockefeller.edu and uses the same filesystem as the standard login04/RHEL 7 system. 

Don't worry if you need to submit a job to a partition on the old system (for example, the cao nodes!) Cursor can do it via ssh.

How to set up your server:
1. If you don't have conda yet, install miniforge.
   - Download the appropriate installer for your system:
     ```bash
     # For Linux:
     wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
     
     # For macOS:
     wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh
     ```
   - Make the installer executable:
     ```bash
     chmod +x Miniforge3-*.sh
     ```
   - Run the installer:
     ```bash
     ./Miniforge3-*.sh
     ```
   - Follow the prompts and accept the license agreement
   - Initialize conda for your shell:
     ```bash
     # For bash:
     conda init bash
     
     # For zsh:
     conda init zsh
     ```
   - Restart your terminal or run:
     ```bash
     # For bash:
     source ~/.bashrc
     
     # For zsh:
     source ~/.zshrc
     ```
   - Verify installation:
     ```bash
     conda --version
     ```
   - Configure conda to use strict channel priority:
     ```bash
     conda config --set channel_priority strict
     ```
   - Add conda-forge as the default channel:
     ```bash
     conda config --add channels conda-forge
     ```

2. Set up ssh connections
   - Generate an SSH key pair (if you don't already have one):
     ```bash
     # Generate an ed25519 key (recommended)
     ssh-keygen -t ed25519 -C "your_email@example.com"
     
     # Or if you need RSA for older systems
     ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
     ```
   - Press Enter to save in the default location (~/.ssh/id_ed25519 or ~/.ssh/id_rsa)
   - Enter a secure passphrase (recommended) or press Enter for no passphrase
   - Copy your public key:
     ```bash
     # For ed25519
     cat ~/.ssh/id_ed25519.pub
     
     # For RSA
     cat ~/.ssh/id_rsa.pub
     ```
   - Add the key to both login nodes:
     ```bash
     # For login04
     ssh-copy-id -i ~/.ssh/id_ed25519.pub username@login04-hpc.rockefeller.edu
     
     # For login05
     ssh-copy-id -i ~/.ssh/id_ed25519.pub username@login05-hpc.rockefeller.edu
     ```
   - Test your connections:
     ```bash
     ssh username@login04-hpc.rockefeller.edu
     ssh username@login05-hpc.rockefeller.edu
     ```

3. Configure Cursor for remote development
   - Open Cursor
   - Click on the "Remote" button in the bottom left corner
   - Click "Add New SSH Host"
   - Enter the following information for each login node:
     
     For login04:
     - Host: login04-hpc.rockefeller.edu
     - User: your_username
     - Private Key Path: ~/.ssh/id_ed25519 (or id_rsa)
     
     For login05:
     - Host: login05-hpc.rockefeller.edu
     - User: your_username
     - Private Key Path: ~/.ssh/id_ed25519 (or id_rsa)
   
   - Click "Connect" for each host
   - You may need to enter your SSH key passphrase if you set one
   - Once connected, you can open folders and files on the remote server

Note: If you're using Windows, you'll need to:
1. Install OpenSSH for Windows (available in Windows 10 and later)
2. Use the Windows Terminal or PowerShell
3. The SSH key path in Cursor should be in Windows format (e.g., C:\Users\YourUsername\.ssh\id_ed25519)