//
//  ContentView.swift
//  BaseCrawler-Mac
//
//  Created by Christopher M. Clendening on 2/18/26.
//

import SwiftUI
import SwiftData

struct ContentView: View {
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \DatabaseConnection.name) private var connections: [DatabaseConnection]

    @State private var selectedConnection: DatabaseConnection?
    @State private var showingAddConnection: Bool = false
    @State private var searchText: String = ""

    private var filteredConnections: [DatabaseConnection] {
        if searchText.isEmpty {
            return connections
        }
        return connections.filter {
            $0.name.localizedCaseInsensitiveContains(searchText) ||
            $0.type.rawValue.localizedCaseInsensitiveContains(searchText) ||
            $0.host.localizedCaseInsensitiveContains(searchText)
        }
    }

    var body: some View {
        NavigationSplitView {
            sidebar
        } detail: {
            detailPanel
        }
        .sheet(isPresented: $showingAddConnection) {
            AddConnectionView()
        }
    }

    // MARK: - Sidebar

    private var sidebar: some View {
        Group {
            if connections.isEmpty {
                emptyState
            } else {
                List(selection: $selectedConnection) {
                    ForEach(filteredConnections) { connection in
                        ConnectionRow(connection: connection)
                            .tag(connection)
                    }
                    .onDelete(perform: deleteConnections)
                }
                .searchable(text: $searchText, placement: .sidebar, prompt: "Search connections")
            }
        }
        .navigationSplitViewColumnWidth(min: 200, ideal: 240, max: 320)
        .navigationTitle("BaseCrawler")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    showingAddConnection = true
                } label: {
                    Label("Add Connection", systemImage: "plus")
                }
                .help("Add a new database connection")
            }
        }
    }

    // MARK: - Detail Panel

    @ViewBuilder
    private var detailPanel: some View {
        if let connection = selectedConnection {
            ConnectionDetailView(connection: connection)
        } else {
            emptyDetail
        }
    }

    // MARK: - Empty States

    private var emptyState: some View {
        VStack(spacing: 12) {
            Image(systemName: "cylinder.split.1x2")
                .font(.system(size: 40))
                .foregroundStyle(.tertiary)
            Text("No Connections")
                .font(.headline)
                .foregroundStyle(.secondary)
            Button("Add Connection") {
                showingAddConnection = true
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .navigationTitle("BaseCrawler")
    }

    private var emptyDetail: some View {
        VStack(spacing: 12) {
            Image(systemName: "arrow.left.square")
                .font(.system(size: 40))
                .foregroundStyle(.tertiary)
            Text("Select a Connection")
                .font(.headline)
                .foregroundStyle(.secondary)
            Text("Choose a saved database connection from the sidebar.")
                .font(.subheadline)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Actions

    private func deleteConnections(at offsets: IndexSet) {
        withAnimation {
            for index in offsets {
                let connection = filteredConnections[index]
                if selectedConnection == connection {
                    selectedConnection = nil
                }
                modelContext.delete(connection)
            }
        }
    }
}

// MARK: - Sidebar Row

struct ConnectionRow: View {
    let connection: DatabaseConnection

    @State private var isReachable: Bool? = nil  // nil = unknown, true = up, false = down

    private var typeColor: Color {
        switch connection.type {
        case .postgresql: return Color(red: 0x33 / 255, green: 0x67 / 255, blue: 0x91 / 255)
        case .mysql:      return Color(red: 0xF2 / 255, green: 0x91 / 255, blue: 0x11 / 255)
        case .sqlite:     return Color(red: 0x0F / 255, green: 0x80 / 255, blue: 0xCC / 255)
        case .mssql:      return Color(red: 0xCC / 255, green: 0x29 / 255, blue: 0x27 / 255)
        case .oracle:     return Color(red: 0xF8 / 255, green: 0x00 / 255, blue: 0x00 / 255)
        case .mongodb:    return Color(red: 0x4D / 255, green: 0xB3 / 255, blue: 0x3D / 255)
        case .redis:      return Color(red: 0xDC / 255, green: 0x38 / 255, blue: 0x2D / 255)
        }
    }

    var body: some View {
        HStack(spacing: 10) {
            ZStack {
                RoundedRectangle(cornerRadius: 7, style: .continuous)
                    .fill(typeColor.opacity(0.15))
                    .frame(width: 32, height: 32)
                Image(systemName: connection.type.systemImage)
                    .font(.system(size: 14))
                    .foregroundStyle(typeColor)
            }

            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 5) {
                    Text(connection.name)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .lineLimit(1)

                    Circle()
                        .fill(statusColor)
                        .frame(width: 7, height: 7)
                }
                Text(connection.host.isEmpty ? connection.type.rawValue : "\(connection.type.rawValue) · \(connection.host)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
        }
        .padding(.vertical, 2)
        .task(id: connection.id) {
            await pollReachability()
        }
    }

    private var statusColor: Color {
        switch isReachable {
        case .none:  return .gray.opacity(0.5)
        case true:   return .green
        case false:  return .red
        }
    }

    private func pollReachability() async {
        // SQLite files are always "reachable" locally
        guard connection.type != .sqlite else {
            isReachable = true
            return
        }
        
        guard !connection.host.isEmpty else {
            isReachable = false
            return
        }
        
        guard (1...65535).contains(connection.port) else {
            isReachable = false
            return
        }
        
        while !Task.isCanceled {
            isReachable = await DatabaseConnectionService.checkReachability(connection)
            try? await Task.sleep(for: .seconds(10))
        }
    }
}

#Preview {
    ContentView()
        .modelContainer(for: DatabaseConnection.self, inMemory: true)
}
