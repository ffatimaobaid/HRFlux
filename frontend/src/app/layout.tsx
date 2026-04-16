import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/hooks/useAuth";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "HRFLUX | AI HR Assistant",
  description: "Modern, AI-powered HR management system.",
};

import { AntdRegistry } from "@ant-design/nextjs-registry";
import { ConfigProvider, App } from "antd";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <AntdRegistry>
          <ConfigProvider
            theme={{
              token: {
                colorPrimary: '#7b2ff7',
                borderRadius: 8,
                colorBgContainer: '#ffffff',
                colorBgLayout: '#faf5ff',
                fontFamily: 'var(--font-geist-sans)',
                controlHeight: 40,
                colorBorder: '#f0f0f0',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
              },
              components: {
                Button: {
                  boxShadow: 'none',
                  controlOutline: 'none',
                  colorTextLightSolid: '#ffffff',
                },
                Input: {
                  activeShadow: 'none',
                }
              }
            }}
          >
            <App>
              <AuthProvider>
                {children}
              </AuthProvider>
            </App>
          </ConfigProvider>
        </AntdRegistry>
      </body>
    </html>
  );
}
