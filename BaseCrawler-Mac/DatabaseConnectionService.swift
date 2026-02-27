//
//  DatabaseConnectionService.swift
//  BaseCrawler-Mac
//
//  Created by Christopher M. Clendening on 2/18/26.
//

import Foundation

// MARK: - Fallback Tester for Unsupported Databases

class FallbackTester: DatabaseConnectionTester {
    func testConnection(
        host: String,
        port: Int,
        username: String,
        password: String,
        database: String,
        useSSL: Bool
    ) async -> ConnectionTestResult {
        // For unsupported database types, fall back to TCP reachability check
        return await testReachability(host: host, port: port)
    }
}

// MARK: - Database Connection Service

class DatabaseConnectionService {
    
    /// Get the appropriate tester for a database type
    static func getTester(for type: DatabaseType) -> DatabaseConnectionTester {
        switch type {
        case .postgresql:
            return PostgreSQLTester()
        case .mysql:
            return MySQLTester()
        case .sqlite:
            return SQLiteTester()
        case .mongodb:
            return MongoDBTester()
        case .redis:
            return RedisTester()
        case .mssql, .oracle:
            // These database types are not yet implemented, use fallback
            return FallbackTester()
        }
    }
    
    /// Test a database connection
    static func testConnection(_ connection: DatabaseConnection) async -> ConnectionTestResult {
        let tester = getTester(for: connection.type)
        
        return await tester.testConnection(
            host: connection.host,
            port: connection.port,
            username: connection.username,
            password: connection.password,
            database: connection.database,
            useSSL: connection.useSSL
        )
    }
    
    /// Quick check if a connection is reachable (for periodic polling)
    static func checkReachability(_ connection: DatabaseConnection) async -> Bool {
        let result = await testConnection(connection)
        return result.isSuccess
    }
}
