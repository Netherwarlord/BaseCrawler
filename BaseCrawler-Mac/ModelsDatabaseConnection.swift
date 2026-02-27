//
//  DatabaseConnection.swift
//  BaseCrawler-Mac
//
//  Created by Christopher M. Clendening on 2/18/26.
//

import Foundation
import SwiftData

enum DatabaseType: String, Codable, CaseIterable {
    case postgresql = "PostgreSQL"
    case mysql = "MySQL"
    case sqlite = "SQLite"
    case mssql = "SQL Server"
    case oracle = "Oracle"
    case mongodb = "MongoDB"
    case redis = "Redis"

    var systemImage: String {
        switch self {
        case .postgresql: return "cylinder.split.1x2"
        case .mysql:      return "cylinder.split.1x2"
        case .sqlite:     return "internaldrive"
        case .mssql:      return "server.rack"
        case .oracle:     return "cylinder"
        case .mongodb:    return "leaf"
        case .redis:      return "bolt.horizontal"
        }
    }
}

@Model
final class DatabaseConnection {
    var id: UUID
    var name: String
    var type: DatabaseType
    var host: String
    var port: Int
    var username: String
    var password: String
    var database: String
    var notes: String
    var dateAdded: Date
    var useSSL: Bool

    init(
        name: String,
        type: DatabaseType = .postgresql,
        host: String = "localhost",
        port: Int = 5432,
        username: String = "",
        password: String = "",
        database: String = "",
        notes: String = "",
        useSSL: Bool = false
    ) {
        self.id = UUID()
        self.name = name
        self.type = type
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.notes = notes
        self.dateAdded = Date()
        self.useSSL = useSSL
    }
}

extension DatabaseType {
    /// Returns the default port number for each database type.
    var defaultPort: Int {
        switch self {
        case .postgresql: return 5432
        case .mysql:      return 3306
        case .sqlite:     return 0
        case .mssql:      return 1433
        case .oracle:     return 1521
        case .mongodb:    return 27017
        case .redis:      return 6379
        }
    }
}
