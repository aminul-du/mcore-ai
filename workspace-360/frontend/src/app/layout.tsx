import "./globals.css";
import AudioToolbar from "../components/AudioToolbar";

export const metadata = {
  title: "MCORE Workspace 360",
  description: "Sovereign Multi-Cloud Engineering Workspace",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AudioToolbar />
        {children}
      </body>
    </html>
  );
}
