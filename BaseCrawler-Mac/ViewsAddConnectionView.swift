//
//  AddConnectionView.swift
//  BaseCrawler-Mac
//
//  Created by Christopher M. Clendening on 2/18/26.
//

import SwiftUI
import SwiftData

struct AddConnectionView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss

    @State private var name: String = ""
    @State private var type: DatabaseType = .postgresql
    @State private var host: String = "localhost"
    @State private var port: String = "5432"
    @State private var username: String = ""
    @State private var password: String = ""
    @State private var database: String = ""
    @State private var notes: String = ""
    @State private var useSSL: Bool = false

    private var isFormValid: Bool {
        !name.trimmingCharacters(in: .whitespaces).isEmpty &&
        !host.trimmingCharacters(in: .whitespaces).isEmpty
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Image(systemName: "plus.circle.fill")
                    .foregroundStyle(.blue)
                    .font(.title2)
                Text("New Database Connection")
                    .font(.headline)
                Spacer()
            }
            .padding()

            Divider()

            Form {
                Section("Connection Identity") {
                    TextField("Connection Name", text: $name)
                    Picker("Database Type", selection: $type) {
                        ForEach(DatabaseType.allCases, id: \.self) { dbType in
                            Label(dbType.rawValue, systemImage: dbType.systemImage)
                                .tag(dbType)
                        }
                    }
                    .onChange(of: type) { _, newType in
                        if type != .sqlite {
                            port = String(newType.defaultPort)
                        }
                    }
                }

                Section("Host & Port") {
                    TextField("Host", text: $host)
                        .disabled(type == .sqlite)
                    if type != .sqlite {
                        TextField("Port", text: $port)
                            .onChange(of: port) { _, newValue in
                                port = newValue.filter(\.isNumber)
                            }
                    }
                }

                Section("Authentication") {
                    TextField("Username", text: $username)
                    SecureField("Password", text: $password)
                }

                Section("Database") {
                    TextField(type == .sqlite ? "File Path" : "Database Name", text: $database)
                    Toggle("Use SSL", isOn: $useSSL)
                        .disabled(type == .sqlite || type == .mongodb || type == .redis)
                }

                Section("Notes") {
                    TextEditor(text: $notes)
                        .frame(minHeight: 60, maxHeight: 120)
                        .font(.body)
                }
            }
            .formStyle(.grouped)

            Divider()

            // Footer buttons
            HStack {
                Button("Cancel", role: .cancel) {
                    dismiss()
                }
                .keyboardShortcut(.escape)

                Spacer()

                Button("Add Connection") {
                    saveConnection()
                }
                .keyboardShortcut(.return)
                .buttonStyle(.borderedProminent)
                .disabled(!isFormValid)
            }
            .padding()
        }
        .frame(minWidth: 420, idealWidth: 480, minHeight: 520)
    }

    private func saveConnection() {
        let connection = DatabaseConnection(
            name: name.trimmingCharacters(in: .whitespaces),
            type: type,
            host: host.trimmingCharacters(in: .whitespaces),
            port: Int(port) ?? type.defaultPort,
            username: username.trimmingCharacters(in: .whitespaces),
            password: password,
            database: database.trimmingCharacters(in: .whitespaces),
            notes: notes.trimmingCharacters(in: .whitespaces),
            useSSL: useSSL
        )
        modelContext.insert(connection)
        dismiss()
    }
}

#Preview {
    AddConnectionView()
        .modelContainer(for: DatabaseConnection.self, inMemory: true)
}
