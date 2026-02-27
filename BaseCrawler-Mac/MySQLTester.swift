//
//  MySQLTester.swift
//  BaseCrawler-Mac
//
//  Created by Christopher M. Clendening on 2/18/26.
//

import Foundation
import MySQLNIO
import NIOCore
import NIOPosix
import Logging

class MySQLTester: DatabaseConnectionTester {
    func testConnection(
        host: String,
        port: Int,
        username: String,
        password: String,
        database: String,
        useSSL: Bool
    ) async -> ConnectionTestResult {
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
            eventLoopGroup.shutdownGracefully { _ in }
        }
        
        do {
            let logger = Logger(label: "mysql-test")
            let address = try SocketAddress.makeAddressResolvingHost(host, port: port)
            
            return try await withThrowingTaskGroup(of: ConnectionTestResult.self) { group in
                group.addTask {
                    do {
                        let connection = try await MySQLConnection.connect(
                            to: address,
                            username: username,
                            database: database.isEmpty ? username : database,
                            password: password,
                            tlsConfiguration: nil,
                            logger: logger,
                            on: eventLoopGroup.next()
                        ).get()

                        try? connection.close().wait()
                        return .success
                        
                    } catch {
                        let errorMsg = "\(error)"
                        if errorMsg.contains("Access denied") {
                            return .failure(.authenticationFailed("Invalid username or password"))
                        } else if errorMsg.contains("Unknown database") {
                            return .failure(.databaseNotFound(database))
                        } else {
                            return .failure(.networkError(errorMsg))
                        }
                    }
                }
                
                group.addTask {
                    try await Task.sleep(for: .seconds(10))
                    return .failure(.connectionTimeout)
                }
                
                let result = try await group.next()!
                group.cancelAll()
                return result
            }
            
        } catch {
            return .failure(.networkError(error.localizedDescription))
        }
    }
}
