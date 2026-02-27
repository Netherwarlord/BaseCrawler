//
//  PostgreSQLTester.swift
//  BaseCrawler-Mac
//
//  Created by Christopher M. Clendening on 2/18/26.
//

import Foundation
import PostgresNIO
import NIOCore
import NIOPosix
import Logging

class PostgreSQLTester: DatabaseConnectionTester {
    func testConnection(
        host: String,
        port: Int,
        username: String,
        password: String,
        database: String,
        useSSL: Bool
    ) async -> ConnectionTestResult {
        // Validate inputs
        guard !host.isEmpty else {
            return .failure(.invalidConfiguration("Host cannot be empty"))
        }
        
        guard (1...65535).contains(port) else {
            return .failure(.invalidConfiguration("Invalid port number"))
        }
        
        guard !username.isEmpty else {
            return .failure(.invalidConfiguration("Username cannot be empty"))
        }
        
        let eventLoopGroup = MultiThreadedEventLoopGroup(numberOfThreads: 1)
        defer {
            try? eventLoopGroup.syncShutdownGracefully()
        }
        
        do {
            let logger = Logger(label: "postgres-test")
            
            // Configure connection
            let config = PostgresConnection.Configuration(
                host: host,
                port: port,
                username: username,
                password: password,
                database: database.isEmpty ? nil : database,
                tls: .disable
            )
            
            // Attempt connection with timeout
            return try await withThrowingTaskGroup(of: ConnectionTestResult.self) { group in
                group.addTask {
                    do {
                        let connection = try await PostgresConnection.connect(
                            on: eventLoopGroup.next(),
                            configuration: config,
                            id: 1,
                            logger: logger
                        )
                        
                        // Close the connection
                        connection.close()
                        
                        return .success
                    } catch let error as PSQLError {
                        if case .connectionError = error.code {
                            return .failure(.networkError(error.localizedDescription))
                        } else if case .authenticationError = error.code {
                            return .failure(.authenticationFailed("Invalid username or password"))
                        } else {
                            let errorMsg = "\(error)"
                            if errorMsg.contains("database") && errorMsg.contains("does not exist") {
                                return .failure(.databaseNotFound(database))
                            }
                            return .failure(.unknownError(errorMsg))
                        }
                    } catch {
                        return .failure(.unknownError(error.localizedDescription))
                    }
                }
                
                // Add timeout task
                group.addTask {
                    try await Task.sleep(for: .seconds(10))
                    return .failure(.connectionTimeout)
                }
                
                let result = try await group.next()!
                group.cancelAll()
                return result
            }
            
        } catch {
            return .failure(.unknownError(error.localizedDescription))
        }
    }
}
