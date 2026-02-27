//
//  ConnectionDetailView.swift
//  BaseCrawler-Mac
//
//  Created by Christopher M. Clendening on 2/18/26.
//

import SwiftUI
import SwiftData

// MARK: - Connection Status

enum ConnectionStatus: Equatable {
    case idle
    case checking
    case connected
    case failed(String)

    var label: String {
        switch self {
        case .idle:            return "Not Tested"
        case .checking:        return "Checking…"
        case .connected:       return "Reachable"
        case .failed(let msg): return msg
        }
    }

    var color: Color {
        switch self {
        case .idle:      return .secondary
        case .checking:  return .orange
        case .connected: return .green
        case .failed:    return .red
        }
    }

    var systemImage: String {
        switch self {
        case .idle:      return "circle.dotted"
        case .checking:  return "arrow.trianglehead.2.clockwise"
        case .connected: return "checkmark.circle.fill"
        case .failed:    return "xmark.circle.fill"
        }
    }
}

struct ConnectionDetailView: View {
    @Bindable var connection: DatabaseConnection
    @State private var isEditing: Bool = false
    @State private var showDeleteConfirmation: Bool = false
    @Environment(\.modelContext) private var modelContext

    // Connection status
    @State private var connectionStatus: ConnectionStatus = .idle

    // Temporary edit state
    @State private var editName: String = ""
    @State private var editHost: String = ""
    @State private var editPort: String = ""
    @State private var editUsername: String = ""
    @State private var editPassword: String = ""
    @State private var editDatabase: String = ""
    @State private var editNotes: String = ""
    @State private var editType: DatabaseType = .postgresql
    @State private var editUseSSL: Bool = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Hero Header
                connectionHeader

                Divider()

                if isEditing {
                    editForm
                } else {
                    detailCards
                }
            }
            .padding(24)
        }
        .background(Color(NSColor.windowBackgroundColor))
        .navigationTitle(connection.name)
        .onAppear {
            connectionStatus = .idle
        }
        .onChange(of: connection.id) {
            connectionStatus = .idle
        }
        .toolbar {
            ToolbarItemGroup {
                if isEditing {
                    Button("Cancel") {
                        cancelEditing()
                    }
                    Button("Save") {
                        saveEdits()
                    }
                    .buttonStyle(.borderedProminent)
                } else {
                    Button {
                        Task { await testConnection() }
                    } label: {
                        Label("Test Connection", systemImage: "network")
                    }
                    .disabled(connectionStatus == .checking)
                    .help("Test whether the host is reachable")

                    Button {
                        beginEditing()
                    } label: {
                        Label("Edit", systemImage: "pencil")
                    }

                    Button(role: .destructive) {
                        showDeleteConfirmation = true
                    } label: {
                        Label("Delete", systemImage: "trash")
                    }
                    .confirmationDialog(
                        "Delete \"\(connection.name)\"?",
                        isPresented: $showDeleteConfirmation,
                        titleVisibility: .visible
                    ) {
                        Button("Delete", role: .destructive) {
                            modelContext.delete(connection)
                        }
                        Button("Cancel", role: .cancel) {}
                    } message: {
                        Text("This action cannot be undone.")
                    }
                }
            }
        }
    }

    // MARK: - Header

    private var connectionHeader: some View {
        HStack(spacing: 16) {
            ZStack {
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(typeColor.opacity(0.15))
                    .frame(width: 56, height: 56)
                Image(systemName: connection.type.systemImage)
                    .font(.title2)
                    .foregroundStyle(typeColor)
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(connection.name)
                    .font(.title2)
                    .fontWeight(.semibold)
                Text(connection.type.rawValue)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Text("Added \(connection.dateAdded.formatted(date: .abbreviated, time: .shortened))")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 6) {
                if connection.useSSL {
                    Label("SSL", systemImage: "lock.fill")
                        .font(.caption)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(.green.opacity(0.12), in: Capsule())
                        .foregroundStyle(.green)
                }

                // Connection status badge
                HStack(spacing: 4) {
                    if case .checking = connectionStatus {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Image(systemName: connectionStatus.systemImage)
                    }
                    Text(connectionStatus.label)
                        .font(.caption)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(connectionStatus.color.opacity(0.12), in: Capsule())
                .foregroundStyle(connectionStatus.color)
            }
        }
    }

    // MARK: - Detail Cards (Read-Only)

    private var detailCards: some View {
        VStack(spacing: 16) {
            DetailCard(title: "Connection") {
                DetailRow(label: "Host", value: connection.host.isEmpty ? "—" : connection.host)
                if connection.type != .sqlite {
                    Divider().padding(.leading, 100)
                    DetailRow(label: "Port", value: connection.port == 0 ? "—" : String(connection.port))
                }
                Divider().padding(.leading, 100)
                DetailRow(label: "Database", value: connection.database.isEmpty ? "—" : connection.database)
            }

            DetailCard(title: "Authentication") {
                DetailRow(label: "Username", value: connection.username.isEmpty ? "—" : connection.username)
                Divider().padding(.leading, 100)
                DetailRow(label: "Password", value: connection.password.isEmpty ? "—" : String(repeating: "●", count: min(connection.password.count, 12)))
            }

            DetailCard(title: "Security") {
                DetailRow(label: "SSL Enabled", value: connection.useSSL ? "Yes" : "No")
            }

            if !connection.notes.isEmpty {
                DetailCard(title: "Notes") {
                    Text(connection.notes)
                        .font(.body)
                        .foregroundStyle(.primary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 4)
                }
            }

            // Connection String preview
            if connection.type != .sqlite {
                DetailCard(title: "Connection String") {
                    Text(connectionString)
                        .font(.system(.caption, design: .monospaced))
                        .foregroundStyle(.secondary)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    // MARK: - Edit Form

    private var editForm: some View {
        Form {
            Section("Connection Identity") {
                TextField("Connection Name", text: $editName)
                Picker("Database Type", selection: $editType) {
                    ForEach(DatabaseType.allCases, id: \.self) { dbType in
                        Label(dbType.rawValue, systemImage: dbType.systemImage).tag(dbType)
                    }
                }
                .onChange(of: editType) { _, newType in
                    editPort = String(newType.defaultPort)
                }
            }

            Section("Host & Port") {
                TextField("Host", text: $editHost)
                    .disabled(editType == .sqlite)
                if editType != .sqlite {
                    TextField("Port", text: $editPort)
                        .onChange(of: editPort) { _, v in editPort = v.filter(\.isNumber) }
                }
            }

            Section("Authentication") {
                TextField("Username", text: $editUsername)
                SecureField("Password", text: $editPassword)
            }

            Section("Database") {
                TextField(editType == .sqlite ? "File Path" : "Database Name", text: $editDatabase)
                Toggle("Use SSL", isOn: $editUseSSL)
                    .disabled(editType == .sqlite || editType == .mongodb || editType == .redis)
            }

            Section("Notes") {
                TextEditor(text: $editNotes)
                    .frame(minHeight: 60, maxHeight: 120)
            }
        }
        .formStyle(.grouped)
    }

    // MARK: - Helpers

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

    @MainActor
    private func testConnection() async {
        connectionStatus = .checking

        // Use the DatabaseConnectionService to perform actual database connection test
        let result = await DatabaseConnectionService.testConnection(connection)

        switch result {
        case .success:
            connectionStatus = .connected
        case .failure(let error):
            // Prefer localized description if available, otherwise fallback to a generic message
            let message = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            connectionStatus = .failed(message)
        }
    }

    private var connectionString: String {
        let scheme = connection.type.rawValue.lowercased().replacingOccurrences(of: " ", with: "")
        let user = connection.username.isEmpty ? "" : "\(connection.username)@"
        let db = connection.database.isEmpty ? "" : "/\(connection.database)"
        return "\(scheme)://\(user)\(connection.host):\(connection.port)\(db)"
    }

    private func beginEditing() {
        editName = connection.name
        editType = connection.type
        editHost = connection.host
        editPort = String(connection.port)
        editUsername = connection.username
        editPassword = connection.password
        editDatabase = connection.database
        editNotes = connection.notes
        editUseSSL = connection.useSSL
        isEditing = true
    }

    private func saveEdits() {
        connection.name = editName.trimmingCharacters(in: .whitespaces)
        connection.type = editType
        connection.host = editHost.trimmingCharacters(in: .whitespaces)
        connection.port = Int(editPort) ?? editType.defaultPort
        connection.username = editUsername.trimmingCharacters(in: .whitespaces)
        connection.password = editPassword
        connection.database = editDatabase.trimmingCharacters(in: .whitespaces)
        connection.notes = editNotes.trimmingCharacters(in: .whitespaces)
        connection.useSSL = editUseSSL
        isEditing = false
    }

    private func cancelEditing() {
        isEditing = false
    }
}

// MARK: - Reusable Sub-Views

struct DetailCard<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(title.uppercased())
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundStyle(.secondary)
                .padding(.bottom, 6)

            VStack(spacing: 0) {
                content
            }
            .padding(12)
            .background(Color(NSColor.controlBackgroundColor), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
        }
    }
}

struct DetailRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack {
            Text(label)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .frame(width: 90, alignment: .leading)
            Text(value)
                .font(.subheadline)
                .foregroundStyle(.primary)
                .textSelection(.enabled)
            Spacer()
        }
        .padding(.vertical, 4)
    }
}

