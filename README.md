Template repository for using Cursor on the RU HPC cluster.

For best results, you will want to use the new Rocky 9 server (login05), which is compatible with the newest version of Cursor. To get access to Rocky 9, email it_hpc@rockefeller.edu and request onboarding to the Rocky 9 system. Rocky 9 can be accessed by login05-hpc.rockefeller.edu and uses the same filesystem as the standard login04/RHEL 7 system. Don't worry if you need to submit a job to a partition on the old system (for example, the cao nodes!) Cursor can do it via ssh.

You *can* run Cursor with login04, but that operating system is not supported so you may encounter errors.

How to set up your server (do all of this on your local computer--current guide is for Mac)

1. Set up SSH:
    - Generate an SSH key pair (if you don't already have one):
        ```bash
        # Generate an ed25519 key (recommended)
        ssh-keygen -t ed25519 -C "your_email@example.com"
        ```
    - Press Enter to save in the default location (~/.ssh/id_ed25519)
    - Enter a secure passphrase (recommended) or press Enter for no passphrase
    - Copy your public key:
        ```bash
        cat ~/.ssh/id_ed25519.pub
        ```
    - Add the key to whichever login node(s) you want to use:
        ```bash
        # For login04
        ssh-copy-id -i ~/.ssh/id_ed25519.pub username@login04-hpc.rockefeller.edu
        
        # For login05
        ssh-copy-id -i ~/.ssh/id_ed25519.pub username@login05-hpc.rockefeller.edu
        ```
    - Add aliases to your ~/.ssh/config file:
        ```bash
        # Create or edit ~/.ssh/config
        cat >> ~/.ssh/config << 'EOF'
        Host login04
            HostName login04-hpc.rockefeller.edu
            User your_username
            IdentityFile ~/.ssh/id_ed25519
        
        Host login05
            HostName login05-hpc.rockefeller.edu
            User your_username
            IdentityFile ~/.ssh/id_ed25519
        EOF
        ```
    - Test your connections:
        ```bash
        ssh login04
        ssh login05
        ```

2. Install and configure Cursor ssh:
    - Install Cursor from https://www.cursor.com/
    - Open Cursor
    - Click on the "Remote" button in the bottom left corner
    - Click "Add New SSH Host"
    - Enter the following information for each login node:
        
        For login05 (recommended):
        - Host: login05
        - User: your_username
        - Private Key Path: ~/.ssh/id_ed25519
        
        For login04 (can add as well, but may or may not work)
        - Host: login04
        - User: your_username
        - Private Key Path: ~/.ssh/id_ed25519
    
    - Click "Connect" for each host
    - You may need to enter your SSH key passphrase if you set one
    - Once connected, you can open folders and files on the remote server

Note: If you're using Windows, you'll need to:
1. Install OpenSSH for Windows (available in Windows 10 and later)
2. Use the Windows Terminal or PowerShell
3. The SSH key path in Cursor should be in Windows format (e.g., C:\Users\YourUsername\.ssh\id_ed25519)
4. Create the SSH config file at C:\Users\YourUsername\.ssh\config

3. Change Cursor settings to enable auto-run mode (optional):
    - Open Cursor Settings (Cursor -> Settings -> Cursor Settings)
    - Go to "Features"
    - Enable "Auto-run mode". Click OK on the warning (though read it first!)
    - Go to "File Protection"
    - Enable "Delete file protection"
    - Under "Command Denylist", add the following commands:
        ```
        rm
        sudo
        pip
        ```
    - Click "Save" to apply changes

4. Set up your Cursor project folder on your remote system:
    - Create a Cursor project folder in your store folder (e.g. /lustre/fs4/cao_lab/store/aepstein/cursor_projects/cursor_template)
    - Create an intermediate files folder in your scratch folder (e.g. /lustre/4/cao_lab/scratch/aepstein/cursor_projects/cursor_intermediate_files)
    - In your Cursor project folder, create a symlink to the intermediate files folder:
        ```bash
        ln -s /path/to/your/intermediate_files_folder intermediate_files
        ```
    - Copy makerepo.sh to your Cursor project folder:
        ```bash
        cp /lustre/fs4/cao_lab/store/aepstein/cursor_projects/makerepo.sh .
        chmod +x makerepo.sh
        ```

5. Have fun with Cursor!
    - To make a new project, run:
        ```bash
        ./makerepo.sh --name new_project_name
        ```
    - To make a new project by copying an existing local project, run:
        ```bash
        ./makerepo.sh --name new_project_name --template_repo /path/to/existing/repo
        ```
    - To make a new project by copying a GitHub project, run:
        ```bash
        ./makerepo.sh --name new_project_name --template_repo username/repo
        ```
    - To edit your project in Cursor, press Command+Shift+P (or Ctrl+Shift+P on Windows) to open the Command Palette. Type "ssh" and choose "Connect current window to host..." Choose login05. Then open the folder for your project. You're set!

6. Optional: use GitHub:
    - If you install the GitHub client (e.g. with conda install conda-forge::gh) you can use the --github flag to automatically create a GitHub repository for your new project. Talk to me if you have quetsions about setting up GitHub with Cursor and giving the client access to your account. 