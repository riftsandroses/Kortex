"use client"

import * as React from "react"
import {
  Bot,
  SquareTerminal,
  LifeBuoy,
  Send,
  Swords,
} from "lucide-react"

import { NavMain } from "@/components/nav-main"
import { NavSecondary } from "@/components/nav-secondary"
import { NavUser } from "@/components/nav-user"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar variant="inset" {...props} className="border-r border-border">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <a href="/dashboard" className="flex items-center gap-3">
                <div className="flex items-center justify-center rounded-lg bg-transparent">
                  <img
                    src="/KPMG-logo.svg"
                    alt="KPMG Logo"
                    className="h-6 w-auto brightness-0 invert"
                  />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-medium">NORA</span>
                  <span className="truncate text-xs text-muted-foreground">
                    Guardrails Platform
                  </span>
                </div>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <NavMain
          items={[
            {
              title: "Dashboard",
              icon: SquareTerminal,
              items: [
                { title: "Overview", url: "/dashboard" },
                { title: "Kobra Dashboards", url: "#" },
                { title: "Katana Dashboard", url: "#" },
              ],
            },
            {
              title: "Kobra",
              icon: Bot,
              items: [
                { title: "Active Apps", url: "/kobra/active-apps" },
                { title: "LLM Responses", url: "/kobra/llm-responses" },
                { title: "Training Jobs", url: "/kobra/training-jobs" },
                { title: "Available Models", url: "/kobra/available-models" },
              ],
            },
            {
              title: "Katana",
              icon: Swords,
              items: [{ title: "Overview", url: "/katana" }],
            },
          ]}
        />
        <NavSecondary
          items={[
            { title: "Support", url: "/support", icon: LifeBuoy },
            { title: "Feedback", url: "/feedback", icon: Send },
          ]}
          className="mt-auto"
        />
      </SidebarContent>

      <SidebarFooter>
        <NavUser
          user={{
            name: "John Doe",
            email: "john.doe@kpmg.com",
            avatar: "/avatars/shadcn.jpg",
          }}
        />
      </SidebarFooter>
    </Sidebar>
  )
}
