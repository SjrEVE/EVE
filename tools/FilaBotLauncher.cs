using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        string pythonExe = FindPython(baseDir);

        if (string.IsNullOrEmpty(pythonExe) || !File.Exists(pythonExe))
        {
            MessageBox.Show(
                "Không tìm thấy Python để khởi động Fila-Bot!\n\n" +
                "Vui lòng kiểm tra lại bộ cài Python hoặc đặt thư mục python vào cùng thư mục bot.",
                "Fila-Bot — Lỗi Khởi Động",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return;
        }

        string srcDir = Path.Combine(baseDir, "src");
        ProcessStartInfo psi = new ProcessStartInfo();
        psi.FileName = pythonExe;

        string joinedArgs = args != null && args.Length > 0 ? string.Join(" ", args) : "";
        if (string.IsNullOrEmpty(joinedArgs))
        {
            psi.Arguments = "-m fila_bot.ui";
        }
        else if (joinedArgs.StartsWith("cli ", StringComparison.OrdinalIgnoreCase))
        {
            psi.Arguments = "-m fila_bot." + joinedArgs;
        }
        else if (joinedArgs.StartsWith("-m ", StringComparison.OrdinalIgnoreCase))
        {
            psi.Arguments = joinedArgs;
        }
        else
        {
            psi.Arguments = "-m fila_bot.ui " + joinedArgs;
        }

        psi.WorkingDirectory = baseDir;
        psi.UseShellExecute = false;
        psi.EnvironmentVariables["PYTHONPATH"] = srcDir;
        psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";

        try
        {
            Process p = Process.Start(psi);
            if (args != null && args.Length > 0 && joinedArgs.Contains("--smoke"))
            {
                p.WaitForExit();
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show("Lỗi khi khởi động Fila-Bot:\n" + ex.Message, "Fila-Bot Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    static string FindPython(string baseDir)
    {
        string p1 = Path.Combine(baseDir, "python", "python.exe");
        if (File.Exists(p1)) return p1;

        string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string p2 = Path.Combine(localAppData, "hermes", "tools", "python-3.14.9+20261021-win32-x64", "python.exe");
        if (File.Exists(p2)) return p2;

        string toolsDir = Path.Combine(localAppData, "hermes", "tools");
        if (Directory.Exists(toolsDir))
        {
            foreach (string d in Directory.GetDirectories(toolsDir, "python*"))
            {
                string candidate = Path.Combine(d, "python.exe");
                if (File.Exists(candidate)) return candidate;
            }
        }

        string pathEnv = Environment.GetEnvironmentVariable("PATH");
        if (!string.IsNullOrEmpty(pathEnv))
        {
            foreach (string part in pathEnv.Split(';'))
            {
                string trimmed = part.Trim();
                if (string.IsNullOrEmpty(trimmed)) continue;
                if (trimmed.IndexOf("WindowsApps", StringComparison.OrdinalIgnoreCase) >= 0) continue;
                string candidate = Path.Combine(trimmed, "python.exe");
                if (File.Exists(candidate)) return candidate;
            }
        }

        return null;
    }
}
